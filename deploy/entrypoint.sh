#!/usr/bin/env bash
# Self-contained entrypoint for onec-training-mcp.
#
# The MCP_Toolkit.epf shipped in this image has a "headless" startup-parameter
# branch in its form's ПриОткрытии — when 1cv8 is launched with /C "headless",
# the form schedules Подключиться() on a 0.5 s one-shot timer, so no human
# click on "Запустить сервер" is needed.
#
# The async server-start chain inside the form calls ПодключитьВнешнююКомпоненту
# for MCPHttpTransport, ToonConverter, SyntaxHelpReader, ScreenCapture in
# sequence. Each call may raise the platform's "разрешить подключать
# исполнимые бинарные файлы?" dialog (default focus on «Нет»). We dismiss them
# with Shift+Tab+Return in a loop that exits as soon as port 6003 starts
# listening — that's the explicit signal that ЗапускСервера_Финал has fired
# and we should stop sending keystrokes.

set -e

: "${IB_PATH:=/var/1c/ib}"
: "${MCP_EPF:=/opt/mcp/MCP_Toolkit.epf}"
: "${MCP_PORT:=6003}"
: "${DISPLAY:=:99}"
: "${SCREEN_GEOMETRY:=1280x800x24}"
: "${WAIT_FOR_WINDOW_SECS:=60}"
: "${WAIT_FOR_PORT_SECS:=90}"

export DISPLAY HOME=${HOME:-/root}

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }

# ---- 1. Xvfb -----------------------------------------------------------------
log "Starting Xvfb on $DISPLAY ($SCREEN_GEOMETRY)"
Xvfb "$DISPLAY" -screen 0 "$SCREEN_GEOMETRY" -nolisten tcp -ac >/var/log/1c/xvfb.log 2>&1 &
XVFB_PID=$!

for _ in $(seq 1 100); do
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then break; fi
    sleep 0.1
done
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    log "ERROR: Xvfb did not come up on $DISPLAY"
    cat /var/log/1c/xvfb.log >&2 || true
    exit 1
fi

# ---- 2. dbus -----------------------------------------------------------------
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    eval "$(dbus-launch --sh-syntax)"
    export DBUS_SESSION_BUS_ADDRESS DBUS_SESSION_BUS_PID
fi

# ---- 2a. Window manager ------------------------------------------------------
# Xvfb alone doesn't manage focus or _NET_ACTIVE_WINDOW, so xdotool synthetic
# keystrokes never reach the 1cv8 window. fluxbox is a tiny WM that fixes both.
log "Starting fluxbox"
fluxbox >/var/log/1c/fluxbox.log 2>&1 &
WM_PID=$!
sleep 1

# ---- 2b. VNC server (port 5900) ----------------------------------------------
# Mapped only when the user runs `docker run -p 5900:5900` — useful as a manual
# fallback if a future platform version reorders dialogs and breaks the
# dismissal loop below.
log "Starting x11vnc on :5900 (no password)"
x11vnc -display "$DISPLAY" -forever -shared -nopw -rfbport 5900 -bg \
       -o /var/log/1c/vnc.log >/dev/null 2>&1 || \
    log "WARN: x11vnc failed to start"

# ---- 3. 1cv8 with /C "headless" ---------------------------------------------
# IB shipped with no users (1Cv8_no_users.dt), so no auth path runs and the
# .epf opens silently. Headless flag tells the form to autostart the server.
log "Launching 1cv8 against $IB_PATH, loading $MCP_EPF (headless)"
/usr/local/bin/1cv8 ENTERPRISE \
    /F"$IB_PATH" \
    /Execute"$MCP_EPF" \
    /C"headless" \
    "$@" >/var/log/1c/1cv8.log 2>&1 &
ONEC_PID=$!

DISMISSER_PID=""

cleanup() {
    log "Shutting down (1cv8 pid=$ONEC_PID, xvfb pid=$XVFB_PID, wm pid=$WM_PID, dismisser pid=$DISMISSER_PID)"
    [ -n "$DISMISSER_PID" ] && kill -TERM "$DISMISSER_PID" 2>/dev/null || true
    kill -TERM "$ONEC_PID"  2>/dev/null || true
    kill -TERM "$WM_PID"    2>/dev/null || true
    kill -TERM "$XVFB_PID"  2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ---- 4. Dismiss security warnings until the port is up ----------------------
# We can't distinguish "platform dialog visible" from "form visible" through
# xdotool (the 1C modal renders inside the same X11 window), so we send
# Shift+Tab+Return on a heartbeat and watch for port 6003 to start listening.
# Once it does we stop immediately — pressing Return on the form's
# «Остановить сервер» button after that would tear the server down.
#
# Why Shift+Tab+Return: the platform dialog focuses «Нет» (right) by default;
# Shift+Tab moves to «Да» (left) and Return presses it. Same key sequence
# works for all subsequent component-attach warnings in the async chain
# (MCPHttp → ToonConverter → SyntaxHelp → ScreenCapture → server start).

wait_for_window_named() {
    local pat="$1" deadline=$(( SECONDS + ${2:-60} ))
    while [ $SECONDS -lt $deadline ]; do
        if xdotool search --name "$pat" 2>/dev/null | head -1 | grep -q .; then
            return 0
        fi
        sleep 1
    done
    return 1
}

log "Waiting up to ${WAIT_FOR_WINDOW_SECS}s for the demo app window..."
if ! wait_for_window_named "Демонстрационное приложение" "$WAIT_FOR_WINDOW_SECS"; then
    log "WARN: demo app window did not appear within ${WAIT_FOR_WINDOW_SECS}s"
    log "      Check /var/log/1c/1cv8.log for errors."
fi

log "Dismissing security warnings until port $MCP_PORT listens..."
deadline=$(( SECONDS + WAIT_FOR_PORT_SECS ))
port_up=0
while [ $SECONDS -lt $deadline ]; do
    if ss -ltn 2>/dev/null | grep -q ":$MCP_PORT\b"; then
        port_up=1
        break
    fi
    xdotool key --delay 80 shift+Tab 2>/dev/null || true
    xdotool key --delay 80 Return    2>/dev/null || true
    sleep 1
done

if [ $port_up -eq 1 ]; then
    log "MCP server is LISTEN on $MCP_PORT"
else
    log "WARN: port $MCP_PORT did not start listening within ${WAIT_FOR_PORT_SECS}s"
    log "      Connect via VNC (port 5900) or docker exec and inspect manually."
fi

# ---- 4b. Residual-dialog dismisser (lifetime of container) ------------------
# Some native components (notably QueryLineageAnalyzer) are loaded LAZILY on the
# first execute_query / execute_code call — i.e. AFTER port 6003 is already
# listening and the initial dismissal loop above has exited. When that lazy
# load fires, the platform raises "Предупреждение безопасности" with default
# focus on «Нет», and the tool call hangs until somebody answers.
#
# We can't search the dialog by --name (the 1cv8 X windows have no _NET_WM_NAME
# strings, so `xdotool search --name` returns nothing). What we CAN observe is
# focus: when a modal opens, the X11 active window changes from the "form is
# idle" baseline to the modal's window id. We capture the baseline after the
# autostart chain has fully quiesced, then watch for changes. On a change we
# send the same Shift+Tab+Return we used pre-port-up — Shift+Tab moves focus
# from the default «Нет» to «Да», Return clicks it. Once the modal closes the
# active window returns to baseline and we go back to sleep.
#
# This runs only when port 6003 is up (we already know the autostart chain is
# done by then) and only fires on focus changes, so it doesn't churn at the
# form's idle UI.
dismiss_residual_dialogs() {
    # Give the post-port-up state a moment to settle (form repaints, any
    # trailing autostart-chain animations finish).
    sleep 3
    local baseline
    baseline=$(xdotool getactivewindow 2>/dev/null || echo "")
    if [ -z "$baseline" ]; then
        log "WARN: residual-dismisser couldn't read baseline active window; not arming"
        return 0
    fi
    log "Residual-dialog dismisser armed (baseline active window = $baseline)"
    while true; do
        local cur
        cur=$(xdotool getactivewindow 2>/dev/null || echo "")
        if [ -n "$cur" ] && [ "$cur" != "$baseline" ]; then
            log "Focus changed ($baseline -> $cur), dismissing presumed modal"
            xdotool key --delay 80 shift+Tab 2>/dev/null || true
            xdotool key --delay 80 Return    2>/dev/null || true
            # Wait for the modal to actually close (rather than retry immediately
            # and double-press, which could activate something in the form behind it).
            for _ in $(seq 1 10); do
                sleep 0.5
                cur=$(xdotool getactivewindow 2>/dev/null || echo "")
                [ "$cur" = "$baseline" ] && break
            done
        else
            sleep 1
        fi
    done
}

if [ $port_up -eq 1 ]; then
    dismiss_residual_dialogs &
    DISMISSER_PID=$!
fi

# ---- 5. Wait on 1cv8 ---------------------------------------------------------
wait "$ONEC_PID"
EC=$?
log "1cv8 exited with code $EC"
exit "$EC"
