import os

import fire
import torch
import readline
from accelerate import infer_auto_device_map, dispatch_model
from accelerate.utils import get_balanced_memory
from transformers import AutoTokenizer
from modeling_bloom import BloomForCausalLM
from typing import List, Tuple

os.environ["TOKENIZERS_PARALLELISM"] = "false"

max_generate_length: int = 1024


def get_model(model):
    def skip(*args, **kwargs):
        pass

    torch.nn.init.kaiming_uniform_ = skip
    torch.nn.init.uniform_ = skip
    torch.nn.init.normal_ = skip
    model = BloomForCausalLM.from_pretrained(model, torch_dtype=torch.float16)
    return model


def main(
    model_path: str = "tigerbot-7b-sft",
    max_input_length: int = 512,
    max_generate_length: int = 1024,
):
    print(f"loading model: {model_path}...")
    model = get_model(model_path)
    max_memory = get_balanced_memory(model)
    device_map = infer_auto_device_map(model, max_memory=max_memory,
                                       no_split_module_classes=["BloomBlock"])
    print("Using the following device map for the model:", device_map)
    model = dispatch_model(model, device_map=device_map, offload_buffers=True)

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        cache_dir=None,
        model_max_length=max_generate_length,
        padding_side="left",
        truncation_side='left',
        padding=True,
        truncation=True
    )
    if tokenizer.model_max_length is None or tokenizer.model_max_length > 1024:
        tokenizer.model_max_length = 1024
    history = []
    while True:
        raw_text = input("prompt(\"exit\" to end, \"clear\" to clear session) >>> ")
        if not raw_text:
            print('prompt should not be empty!')
            continue
        if raw_text.strip() == "exit":
            print('session ended.')
            break
        if raw_text.strip() == "clear":
            print('session cleared.')
            history = []
            continue
        print("=" * 100)
        for (res, history) in model.stream_chat(
            tokenizer,
            raw_text,
            history,
            max_input_length=max_input_length,
            max_generate_length=max_generate_length
        ):
            if res is not None:
                print("\r" + res, end="")
        print("")
        print("=" * 100)


if __name__ == "__main__":
    fire.Fire(main)
