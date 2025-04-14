import torch

# Check if CUDA is available; if not, fall back to CPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Create two random tensors on the chosen device
while True:
    x = torch.rand((5, 3), device=device)
    y = torch.rand((5, 3), device=device)

    # Perform an operation (element-wise addition in this case)
    z = x + y

print("Tensor x:\n", x)
print("Tensor y:\n", y)
print("Result (x + y):\n", z)
print(f"Result is on device: {z.device}")
