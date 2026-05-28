# 1C Code Bench — Docker deploy

Дополнение к [README.md](README.md). Описывает, как развернуть бенчмарк против
дoкеризованной 1С + MCP Toolkit (Linux), без локальной установки 1С платформы.

С новой архитектурой `BenchmarkRunner` использует:
- `bench/v8pack.py` — pure-Python распаковка/упаковка `.epf`-контейнера
  (вместо вызова `1cv8` Конфигуратора через `OneCEngine.store_processing` /
  `update_processing`);
- `bench/mcp_runner.py` — MCP-клиент, который через `execute_code` гоняет
  патченный `.epf` внутри 1С (вместо запуска `1cv8` Предприятия через
  `OneCEngine.run_processing`).

Поэтому для запуска бенчмарка достаточно одного контейнера с 1С + MCP — на
хосте Python нужен только для самого пайплайна.

## Условные обозначения

В примерах ниже используются два плейсхолдера — подставьте свои значения:

| Плейсхолдер | Что это | Пример |
|---|---|---|
| `$BENCH_HOST_ROOT` | Корень проекта на хосте, где лежит этот репозиторий | Linux: `$HOME/1cbench`; Windows: `C:\projects\1cbench` |
| `$BENCH_MCP_ROOT`  | Путь к bind-mount-у внутри контейнера (как его видит 1С) | По умолчанию `/host/dev` — менять не обязательно |

Те же два имени — это рантайм-переменные окружения, которые читает
`McpRunner` (см. раздел "Запуск бенчмарка против контейнера" ниже).

## Архитектура

```
┌───────────────────────────── Host ──────────────────────────────┐
│                                                                 │
│   Python bench pipeline (this repo)                             │
│     run_bench.py                                                │
│     ├── BenchmarkRunner                                         │
│     │     ├── V8Packer  → bench/v8pack.py (unpack / pack)       │
│     │     └── McpRunner → HTTP → :6003 ──────┐                  │
│     └── tasks/  data/                        │                  │
│                                              │                  │
│   bind mount:                                ▼                  │
│   $BENCH_HOST_ROOT  ⇄  $BENCH_MCP_ROOT (ro)                     │
│           ▲                  ──────────────────────────         │
│           │                  │  Docker container         │      │
│           │                  │  onec-training-mcp:latest │      │
│           │                  │                           │      │
│           │                  │  • 1C Enterprise (training) │    │
│           │                  │  • file IB (/var/1c/ib)     │    │
│           │                  │  • MCP_Toolkit.epf          │    │
│           │                  │  • Xvfb + autostart         │    │
│           │                  │  listens on 6003 (MCP)      │    │
│           │                  │           5900 (VNC)        │    │
│           │                  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

Путь к патченному `.epf` транслируется хостовый → контейнерный через эти же
`BENCH_HOST_ROOT` / `BENCH_MCP_ROOT`, потому что 1С внутри контейнера видит
файлы по контейнерному пути bind-mount-а.

## Где взять образ

Готовый образ (`onec-training-mcp:latest`, ~3.3 GB) лежит в Google Drive:
[onec-training-mcp.tar](https://drive.google.com/file/d/1Z6ZG5p80Fen_vqRvV6XnlAuvSLrjcfL4/view?usp=sharing)
(file id `1Z6ZG5p80Fen_vqRvV6XnlAuvSLrjcfL4`).

Скрипты для скачивания и загрузки в Docker (лежат в `bench/deploy/`):

- `fetch-image.sh` — для Linux / macOS / WSL / Git Bash
- `fetch-image.ps1` — для Windows PowerShell

Оба делают одно и то же: качают tar через `gdown`, выполняют
`docker load`, и удаляют tar.

Вручную:

```bash
pip install gdown
gdown 1Z6ZG5p80Fen_vqRvV6XnlAuvSLrjcfL4 -O onec-training-mcp.tar
docker load -i onec-training-mcp.tar
rm onec-training-mcp.tar
```

### Альтернатива: пересборка образа из исходников

Если нужна именно сборка (например, со своим `.dt` дампом), всё нужное
лежит рядом в `bench/deploy/`:

- `Dockerfile`
- `entrypoint.sh`
- `repack_form_module.py`
- `payload/MCP_Toolkit_linux.epf` + распакованный `Forms/Форма/Ext/Form/Module.bsl`
- `build.sh` (Linux/macOS) и `build.ps1` (Windows)

Внешние артефакты, которые сборка скачать сама не может:

- 1C:Enterprise Linux distro (`setup-training-<ver>-x86_64.run`) — путь
  к каталогу с `.run`-файлом передаётся в `ONEC_DISTRO_DIR`.
- `.dt` дамп базы (`1Cv8_no_users.dt`) — путь к каталогу с дампом передаётся
  в `ONEC_DB_DIR`.

Запуск:

```bash
export ONEC_DISTRO_DIR=/path/to/1c-linux-distro
export ONEC_DB_DIR=/path/to/db-dump-dir
./build.sh
```

Аналогично из PowerShell:

```powershell
$env:ONEC_DISTRO_DIR = "C:\path\to\1c-linux-distro"
$env:ONEC_DB_DIR     = "C:\path\to\db-dump-dir"
.\build.ps1
```

## Запуск контейнера

Готовые скрипты в `bench/deploy/`:

- `run.sh` — Linux / macOS / WSL / Git Bash
- `run.ps1` — Windows PowerShell

Оба читают `BENCH_HOST_ROOT` / `BENCH_MCP_ROOT` из окружения, либо принимают
их явно через параметры. По умолчанию запускают контейнер в foreground
(`--rm`); для фонового режима передайте `DETACH=1 ./run.sh` или
`.\run.ps1 -Detach`.

Эквивалентная ручная команда (Linux / macOS / WSL / Git Bash):

```bash
docker run -d --rm \
    --name onec-mcp \
    -p 6003:6003 \
    -p 5900:5900 \
    -v "$BENCH_HOST_ROOT:$BENCH_MCP_ROOT:ro" \
    onec-training-mcp:latest
```

То же из PowerShell:

```powershell
docker run -d --rm `
    --name onec-mcp `
    -p 6003:6003 `
    -p 5900:5900 `
    -v "${env:BENCH_HOST_ROOT}:${env:BENCH_MCP_ROOT}:ro" `
    onec-training-mcp:latest
```

Что делает entrypoint (`bench/deploy/entrypoint.sh`):
1. поднимает Xvfb + fluxbox;
2. опционально стартует x11vnc на 5900 (для ручного дебага через VNC);
3. запускает `1cv8 ENTERPRISE /F/var/1c/ib /Execute MCP_Toolkit.epf /C"headless"`;
4. автоматически нажимает «Да» в диалогах подключения нативных компонент,
   пока порт 6003 не залистнет;
5. оставляет фоновый watcher, который дисмиссит модалки lazy-loaded
   компонент (например `QueryLineageAnalyzer` подгружается при первом
   `execute_query` уже после того, как порт 6003 поднялся).

Проверить, что MCP отвечает:

```bash
curl -sS -X POST http://localhost:6003/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: text/event-stream, application/json' \
    --data-binary '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

В ответе должно быть `"serverInfo": { "name": "1C MCP Toolkit (Native)" }`.

## Запуск бенчмарка против контейнера

Python и зависимости — на хосте, см. шаги 2–4 раздела "Установка" в
основном [README.md](README.md). 1С платформу ставить **не нужно**.

Перед запуском выставьте те же две переменные окружения, что и в bind-mount-е:

| Переменная | Значение |
|---|---|
| `BENCH_HOST_ROOT` | Абсолютный путь к корню проекта на хосте |
| `BENCH_MCP_ROOT`  | Целевая точка bind-mount-а внутри контейнера (по умолчанию `/host/dev`) |

Без них `McpRunner` отправит в `execute_code` хостовый путь, а 1С внутри
контейнера такой файл не найдёт.

Bash / sh:

```bash
export BENCH_HOST_ROOT=/path/to/your/1cbench
export BENCH_MCP_ROOT=/host/dev
python run_bench.py data/output_<model>.csv
```

PowerShell:

```powershell
$env:BENCH_HOST_ROOT = "C:\path\to\your\1cbench"
$env:BENCH_MCP_ROOT  = "/host/dev"
python run_bench.py data\output_<model>.csv
```

Конфигурация 1С платформы (`DESIGNER_PATH`, `DATABASE_PATH` из основного
README) в этом сценарии не используется — `OneCEngine` остаётся в
репозитории для обратной совместимости, но `BenchmarkRunner` его не
инстанцирует.

## Известные подводные камни

- **Read-only bind mount достаточен.** Патченные `.epf` пишутся на хосте;
  контейнер только читает их. `:ro` — это правильно.
- **MSYS / Git Bash съедает Unix-пути в env vars.** `BENCH_MCP_ROOT=/host/dev`
  через Git Bash превратится в `C:/Program Files/Git/host/dev`. Из
  PowerShell выставляйте напрямую (`$env:BENCH_MCP_ROOT = "/host/dev"`),
  либо удваивайте первый слэш в bash (`BENCH_MCP_ROOT=//host/dev`).
- **Коллизия порта 6003.** Если на машине параллельно работает локальный
  1С MCP Toolkit, оба процесса могут одновременно слушать 6003 и оба
  отдают одинаковый `serverInfo.name`. Различить можно через
  `netstat`/`lsof` по PID. Либо остановите один из процессов, либо
  запустите контейнер на другом порту (`-p 6004:6003`) и передайте
  `MCP_URL=http://localhost:6004/mcp` в окружение `BenchmarkRunner`-а.

