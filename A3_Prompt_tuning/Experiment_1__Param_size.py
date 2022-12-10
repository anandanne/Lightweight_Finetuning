import torch
from torch.utils.data import DataLoader, Dataset
import re
import pandas as pd
import json
import Prompt_Tuning

import os
import sys
sys.path.append('..')
from utils import nethook
from utils import model_utils
from utils import tuning_utils
from utils import testing_utils


####################################################################
torch.cuda.set_device(1)
####################################################################

print("#### Load and preprocess data")
train_df = pd.read_csv("../Data/IMDB_50K_Reviews/train.csv")
validation_df = pd.read_csv("../Data/IMDB_50K_Reviews/validation.csv")
test_df = pd.read_csv("../Data/IMDB_50K_Reviews/test.csv")

CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});|/.*/')

def cleanhtml(raw_html):
  raw_html = raw_html.replace("\\", "")
  raw_html = raw_html.replace("&#039;", "\'")
  cleantext = re.sub(CLEANR, ' ', raw_html)
  split = cleantext.strip().split(" ")
  if(split[0].isnumeric()):
    split = split[1:]
  return " ".join([w for w in split if len(w.strip()) > 0])

class GoEmotions(Dataset):
    def __init__(self, data_frame):
        self.x = []
        self.y = []

        for index, row in data_frame.iterrows():
            self.x.append("<REVIEW>: " + cleanhtml(row["review"]) + " <SENTIMENT>")
            self.y.append(" " + row["sentiment"])
        
    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.x[idx], self.y[idx]


training_dataset = GoEmotions(train_df)
validation_dataset = GoEmotions(validation_df)
test_dataset = GoEmotions(test_df)

print("training dataset size: ", len(training_dataset))
print("validation dataset size: ", len(validation_dataset))
print("test dataset size: ", len(test_dataset))
print()

prefix_size_choices = [2, 4, 8, 16, 32]

######################################################
batch_size = 2
######################################################
training_dataloader = DataLoader(training_dataset, batch_size=batch_size)
validation_dataloader = DataLoader(validation_dataset, batch_size=1)
# testing_dataloader = DataLoader(test_dataset, batch_size=1)


MODEL_NAME = "gpt2-medium"
mt = model_utils.ModelAndTokenizer(MODEL_NAME, low_cpu_mem_usage=False)
model = mt.model
tokenizer = mt.tokenizer
tokenizer.pad_token = tokenizer.eos_token
print(f"Model {MODEL_NAME} initialized")
print()

######################################################
save_path = f"../Saved_weights/EXP1/Prompt-Tuning/{MODEL_NAME}"
######################################################


for prefix_size in prefix_size_choices:
    print("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
    print("prefix size ==> ", prefix_size)
    print("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")

    soft_tokens, tuning_logs = Prompt_Tuning.get_tuned_soft_tokens(
        training_dataloader,
        mt,
        prefix_size = prefix_size,
        num_epochs = 1,
        # limit = 100
    )

    os.makedirs(save_path, exist_ok = True)
    torch.save(soft_tokens, f"{save_path}/prompt_size__{prefix_size}.pth")

    test_results = testing_utils.test(
        validation_dataloader,
        model, tokenizer,
        light_weight_tuning = soft_tokens, algo = "prompt", prefix_size = prefix_size,
        # limit = 100
    )
    
    print(test_results['balanced_accuracy'])
    # print(test_results)

    with open(f"{save_path}/logs_prompt_size__{prefix_size}.json", "w") as f:
        json.dump({
            "tuninig_logs": tuning_logs,
            "test_logs": test_results
        }, f)



