import os, pickle

import torch
from torch.utils.data import Dataset

from transformers.tokenization_utils import trim_batch

from tqdm import tqdm
import mmap

def get_num_lines(file_path):
    fp = open(file_path, "r+")
    buf = mmap.mmap(fp.fileno(), 0)
    lines = 0
    while buf.readline():
        lines += 1
    return lines

def encode_file(tokenizer, data_path, max_length, pad_to_max_length=True, return_tensors="pt"):
    examples = []
    print("data dir:",data_path)
    with open(data_path, "r", encoding="UTF8") as f:
        print("opened.")
        for text in tqdm(f, total=get_num_lines(data_path)):#f.readlines():
            tokenized = tokenizer.batch_encode_plus(
                [text], max_length=max_length, pad_to_max_length=pad_to_max_length, return_tensors=return_tensors,
            )
            examples.append(tokenized)
        print("finished.")
    #with open(data_path + '_', 'wb') as fp:
    #    pickle.dump(examples, fp)
    return examples


class SummarizationDataset(Dataset):
    def __init__(
        self,
        tokenizer,
        data_dir="./cnn-dailymail/cnn_dm/",
        type_path="train",
        max_source_length=1024,
        max_target_length=56,
    ):
        super().__init__()
        self.tokenizer = tokenizer
        if os.path.isfile(os.path.join(data_dir, type_path + ".source_")):
            with open (os.path.join(data_dir, type_path + ".source_"), 'rb') as fp:
                self.source = pickle.load(fp)
        else:
            self.source = encode_file(tokenizer, os.path.join(data_dir, type_path + ".source"), max_source_length)
        if os.path.isfile(os.path.join(data_dir, type_path + ".target_")):
            with open (os.path.join(data_dir, type_path + ".target_"), 'rb') as fp:
                self.target = pickle.load(fp)
        else:
            self.target = encode_file(tokenizer, os.path.join(data_dir, type_path + ".target"), max_source_length)

    def __len__(self):
        return len(self.source)

    def __getitem__(self, index):
        source_ids = self.source[index]["input_ids"].squeeze()
        target_ids = self.target[index]["input_ids"].squeeze()
        src_mask = self.source[index]["attention_mask"].squeeze()
        return {"source_ids": source_ids, "source_mask": src_mask, "target_ids": target_ids}

    @staticmethod
    def trim_seq2seq_batch(batch, pad_token_id):
        y = trim_batch(batch["target_ids"], pad_token_id)
        source_ids, source_mask = trim_batch(batch["source_ids"], pad_token_id, attention_mask=batch["source_mask"])
        return source_ids, source_mask, y

    def collate_fn(self, batch):
        input_ids = torch.stack([x["source_ids"] for x in batch])
        masks = torch.stack([x["source_mask"] for x in batch])
        target_ids = torch.stack([x["target_ids"] for x in batch])
        pad_token_id = self.tokenizer.pad_token_id
        y = trim_batch(target_ids, pad_token_id)
        source_ids, source_mask = trim_batch(input_ids, pad_token_id, attention_mask=masks)
        return {"source_ids": source_ids, "source_mask": source_mask, "target_ids": y}
