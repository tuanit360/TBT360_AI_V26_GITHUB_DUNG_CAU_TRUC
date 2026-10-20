"""Deep-learning image-classification trainer using PyTorch.

Data directory: dataset/<class_name>/<image>.jpg|png|webp.
Images are split independently within each class to keep validation separate.
"""
import csv
import json
import os
import random
import time
from pathlib import Path

import torch
from PIL import Image, ImageOps
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}


def list_images(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError('Không tìm thấy thư mục dữ liệu')
    labels = sorted(p.name for p in root.iterdir() if p.is_dir())
    if len(labels) < 2:
        raise ValueError('Cần ít nhất hai thư mục nhãn (lớp)')
    items = []
    for index, label in enumerate(labels):
        paths = sorted(p for p in (root / label).rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS)
        if len(paths) < 3:
            raise ValueError(f'Lớp {label} cần tối thiểu 3 ảnh (hiện có {len(paths)})')
        items.extend((p, index) for p in paths)
    return labels, items


def split_items(labels, items, seed=42):
    rnd = random.Random(seed)
    train, valid = [], []
    for i, _ in enumerate(labels):
        part = [x for x in items if x[1] == i]
        rnd.shuffle(part)
        n = max(1, min(len(part)-1, round(len(part) * 0.2)))
        valid.extend(part[:n])
        train.extend(part[n:])
    return train, valid


class ImageSet(Dataset):
    def __init__(self, items, training):
        self.items = items
        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.RandomHorizontalFlip() if training else transforms.Lambda(lambda x: x),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        path, label = self.items[index]
        with Image.open(path) as src:
            image = ImageOps.exif_transpose(src).convert('RGB')
        return self.transform(image), label


def make_model(classes, pretrained=False):
    # No automatic downloads or unlicensed hidden weights in offline mode.
    weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    network = models.mobilenet_v3_small(weights=weights)
    network.classifier[-1] = nn.Linear(network.classifier[-1].in_features, classes)
    return network


def run_training(dataset, output, epochs=3, batch_size=8, lr=0.001, use_gpu=False,
                 pretrained=False, on_event=None, stop=None):
    if epochs < 1 or batch_size < 1:
        raise ValueError('epochs và batch size phải lớn hơn 0')
    labels, items = list_images(dataset)
    train, valid = split_items(labels, items)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
    if use_gpu and device.type != 'cuda':
        raise RuntimeError('Đã yêu cầu GPU nhưng PyTorch không phát hiện CUDA')
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    loader_kwargs = dict(batch_size=batch_size, num_workers=0)
    train_loader = DataLoader(ImageSet(train, True), shuffle=True, **loader_kwargs)
    val_loader = DataLoader(ImageSet(valid, False), shuffle=False, **loader_kwargs)
    network = make_model(len(labels), pretrained).to(device)
    optimizer = torch.optim.AdamW(network.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    log_path = output / 'metrics.csv'
    started = time.monotonic()
    best = -1.0
    with log_path.open('w', encoding='utf-8', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=['epoch','loss','accuracy','samples_per_second','elapsed_seconds','device'])
        writer.writeheader()
        for epoch in range(1, epochs+1):
            if stop and stop.is_set():
                break
            network.train()
            total_loss, count = 0.0, 0
            t = time.monotonic()
            for batch_x, batch_y in train_loader:
                if stop and stop.is_set():
                    break
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                optimizer.zero_grad(set_to_none=True)
                outputs = network(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                n = len(batch_y)
                total_loss += loss.item() * n
                count += n
            if count == 0:
                break
            network.eval()
            right, evaluated = 0, 0
            with torch.no_grad():
                for x, y in val_loader:
                    predicted = network(x.to(device)).argmax(dim=1).cpu()
                    right += int((predicted == y).sum())
                    evaluated += len(y)
            accuracy = right / max(1, evaluated)
            row = dict(epoch=epoch, loss=round(total_loss/count, 6), accuracy=round(accuracy, 6),
                       samples_per_second=round(count/max(time.monotonic()-t, 1e-6), 2),
                       elapsed_seconds=round(time.monotonic()-started, 2), device=str(device))
            writer.writerow(row)
            fp.flush()
            checkpoint = {'state_dict': network.cpu().state_dict(), 'labels': labels, 'architecture': 'mobilenet_v3_small', 'input_size': 160, 'epoch': epoch, 'accuracy': accuracy}
            torch.save(checkpoint, output / 'last.pt')
            if accuracy > best:
                best = accuracy
                torch.save(checkpoint, output / 'best.pt')
            network.to(device)
            if on_event:
                on_event(row)
    metadata = {'labels': labels, 'total_images': len(items), 'train_count': len(train), 'validation_count': len(valid),
                'model': 'MobileNetV3 Small', 'pretrained': pretrained, 'device': str(device), 'best_validation_accuracy': best,
                'warning': 'Validation on small or repeated image sets is not evidence of generalization.'}
    (output / 'report.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return metadata


def predict_image(checkpoint_path, image_path):
    # PyTorch checkpoints must come from a trusted local source.
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    labels = checkpoint['labels']
    network = make_model(len(labels), pretrained=False)
    network.load_state_dict(checkpoint['state_dict'])
    network.eval()
    transform = ImageSet([], False).transform
    with Image.open(image_path) as src:
        x = transform(ImageOps.exif_transpose(src).convert('RGB')).unsqueeze(0)
    with torch.no_grad():
        probabilities = torch.softmax(network(x), dim=1)[0]
    return sorted([{'label': label, 'probability': round(float(p), 4)} for label, p in zip(labels, probabilities)], key=lambda x: -x['probability'])
