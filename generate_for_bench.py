import os

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from llm.llm_provider import create_provider, LLMProvider

load_dotenv()

MAX_TOKENS = 10000
TEMPERATURE = 0.5
MAX_RETRIES = 5

# Provider configuration from .env
PROVIDER_TYPE = os.getenv("PROVIDER_TYPE", "anthropic")
MODEL_NAME = os.getenv("MODEL_NAME", "sonnet-4-5")
MODEL_ID = os.getenv("MODEL_ID", "claude-sonnet-4-5-20250929")
# Toggle model reasoning/thinking mode (used by the vllm provider).
REASONING = os.getenv("REASONING", "false").strip().lower() in ("1", "true", "yes", "on")

OUTPUT_FILE = f"data/output_trial8_{MODEL_NAME}.csv"

SYSTEM_PROMPT = "Вы профессиональный разработчик 1С, который пишет код на языке 1С."

USER_PROMPT_MD = """
Дана следующая задача:
[task]

Контекстная информация о структуре конфигурации 1С:
```
[context]
```

Ваша задача - написать полное решение на 1С, которое реализует требуемую функциональность.
Пишите чистый, эффективный код, следуя лучшим практикам 1С.
Требования: 
- начинай секцию кода с "```1c" и заканчивай "```"
- ВСЕГДА выделяй новую строку в текстах запросов символом |
- Текст запроса должен начинаться так:
Запрос.Текст = 
"ВЫБРАТЬ ...
|<вторая строка запроса>

Код:"""

SOURCE_FILE = "data/stage_tasks6.csv"


class LLMRunner:

    def __init__(self, filename, provider: LLMProvider):
        if not provider:
            raise ValueError("LLM provider must be specified.")
        self.api = provider
        self.examples = []
        self.df = pd.read_csv(filename)
        self.examples.extend(self.process_file_full(filename))

    def generate_all(self, result_filename):
        if os.path.exists(result_filename):
            existing_df = pd.read_csv(result_filename)
            existing_df.fillna("", inplace=True)
            records_to_save = existing_df.to_dict(orient="records")
            print(f"Found existing output file '{result_filename}'. Regenerating only empty outputs.")
        else:
            records_to_save = [dict(ex) for ex in self.examples]
            for record in records_to_save:
                record["output"] = ""
                record["thinking"] = ""

        for i, record in tqdm(enumerate(records_to_save), total=len(records_to_save)):
            existing_output = str(record.get("output", "")).strip()
            if existing_output:
                continue
            output = self.generate_sample_full_module(record)
            if output is None or not str(output).strip():
                print(f"Sample {i}: failed to generate after {MAX_RETRIES} attempts. Leaving output empty.")
                record["output"] = ""
                record["thinking"] = ""
            else:
                record["output"] = output
                record["thinking"] = self._format_reasoning(self.api.last_reasoning)
            pd.DataFrame(records_to_save).to_csv(result_filename, index=False)
        return records_to_save

    @staticmethod
    def _format_reasoning(reasoning):
        if not reasoning:
            return ""
        if isinstance(reasoning, list):
            return "[$$$]".join(r for r in reasoning if r)
        return str(reasoning)

    def build_prompt(self, example):
        task = example["task"]
        context = example["context"]
        prompt = USER_PROMPT_MD
        prompt = prompt.replace("[task]", task)
        prompt = prompt.replace("[context]", context)
        return prompt

    @staticmethod
    def extract_code(output):
        if not output:
            return None
        output = output.strip()
        if "```1c" not in output:
            return output
        if "</think>" in output:
            output = output.split("</think>")[1]
        lines = output.split("\n")
        code = []
        code_started = False
        for line in lines:
            if line.startswith("```1c") or line.startswith("---"):
                code_started = True
                continue
            if (line.startswith("```") or line.startswith("---")) and code_started:
                code_started = False
                break
            if code_started:
                code.append(line)
        return "\n".join(code)

    def generate_sample_full_module(self, sample):
        prompt = self.build_prompt(sample)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                output = self.api.generate(
                    prompt,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    n=1,
                )
                if isinstance(output, list):
                    outputs = [self.extract_code(out) for out in output]
                    result = "[$$$]".join(o for o in outputs if o)
                else:
                    result = self.extract_code(output)
                if result and str(result).strip():
                    return result
                print(f"Attempt {attempt}/{MAX_RETRIES}: empty generation result.")
            except Exception as e:
                print(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
        return None

    @staticmethod
    def process_file_full(file_path):
        examples = []
        df = pd.read_csv(file_path)
        df.fillna("", inplace=True)
        for i, row in df.iterrows():
            example = row.to_dict()
            examples.append(example)

        return examples


def main():
    provider_kwargs = {}
    if PROVIDER_TYPE == "vllm":
        provider_kwargs["reasoning"] = REASONING
    provider = create_provider(PROVIDER_TYPE, SYSTEM_PROMPT, MODEL_ID, **provider_kwargs)
    runner = LLMRunner(SOURCE_FILE, provider)
    runner.generate_all(OUTPUT_FILE)


if __name__ == '__main__':
    main()
