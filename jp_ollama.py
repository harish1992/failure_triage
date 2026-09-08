import ollama
from ollama import ResponseError
from functools import partial
from jp_aiconfig import AiConfig

class JpAiTool:
    def __init__(self, model:str):
        self._client = ollama.Client()

        self._ask = partial(
            self._client.chat,
            model=self._validate_model(model),
            format=AiConfig.SCHEMA,
            options={"temperature": 0, "num_ctx": 8192},
            keep_alive="10m",
            )
    
    def _validate_model(self, model:str) -> str:
        try:
            _ = ollama.show(model)
        except:
            print(f"{model} not found switching to default ai model")
            model = 'granite3.1-dense:8b'
        return model

    def ask(self, prompt:str):
        return self._ask(messages=[
            {"role": "system", "content": AiConfig.SYSTEM},
            {"role": "user", "content": prompt},
        ])

class JpResponseError(ResponseError):
    def __init__(self, error_message, status_code=None):
        super().__init__(error_message, status_code)
