import torch
import os

def main():
    os.makedirs("weights", exist_ok=True)
    model = torch.nn.Sequential(
        torch.nn.Linear(512, 256),
        torch.nn.ReLU(),
        torch.nn.Linear(256, 10)
    )
    torch.jit.save(torch.jit.script(model), "weights/model.pt")
    print("Saved dummy model to weights/model.pt")

if __name__ == "__main__":
    main()
