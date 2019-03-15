# 训练可视化tensorboardX
# LR:add_scalar
# acc,loss:add_scalars
# 权重变化：add_histogram
# 图模型结构：add_graph
# 特征降维：add_embedding
# 输出结果混淆矩阵：混淆矩阵
import torch
import time
import copy
from tensorboardX import SummaryWriter
from torch.optim import optimizer

writer = SummaryWriter('../logs/tensorBoardX')


class Acc:
    def __init__(self, name):
        self.name = name
        self.correct = 0
        self.sample = 0
        self.acc_hist = []

    def reset(self):
        self.correct = 0
        self.sample = 0

    def update(self, pred, label):
        pred = torch.argmax(pred, 1)
        correct = pred.size(0) - (pred ^ label).sum().item()
        sample = pred.size(0)
        acc = correct / sample
        scalar_show(writer, acc={self.name: acc})
        self.correct += correct
        self.sample += sample

    def get(self):
        return self.correct / self.sample


class Loss:
    def __init__(self, name):
        self.name = name
        self.loss = 0
        self.sample = 0
        self.loss_hist = []

    def reset(self):
        self.loss = 0
        self.sample = 0

    def update(self, loss):
        scalar_show(writer, loss={self.name: loss})
        self.loss += loss
        self.sample += 1

    def get(self):
        return self.loss / self.sample


class LearningRate:
    def __init__(self):
        self.LR_hist = []


def scalar_show(writer: SummaryWriter, acc=None, loss=None, **kwargs):
    if acc:
        writer.add_scalars("acc", acc)
    if loss:
        writer.add_scalars("loss", loss)
    for key, item in kwargs:
        writer.add_scalar(key, item)


def train_epoch(model, data_loaders, optimizer, device, criterion, scheduler=None):
    acc = Acc("train_batch_acc")
    loss = Loss("train_batch_loss")
    model.train()
    with torch.set_grad_enabled(True):
        for inputs, labels in data_loaders["train"]:
            optimizer.zero_grad()
            inputs = inputs.to(device)
            labels = labels.to(device)
            pred = model(inputs)
            c_loss = criterion(pred, labels)
            c_loss.backward()
            if scheduler:
                scheduler.step()
            else:
                optimizer.step()
            loss.update(c_loss.item())
            acc.update(pred, labels)
            writer.add_scalar("learningRate", optimizer.param_groups[0]['lr'])
        epoch_loss = loss.get()
        epoch_acc = acc.get()
    return epoch_acc, epoch_loss


def valid_epoch(model, data_loaders, device, criterion, model_name, epoch, best_acc):
    acc = Acc("valid_batch_acc")
    loss = Loss("valid_batch_loss")
    model.eval()
    for inputs, labels in data_loaders["valid"]:
        inputs = inputs.to(device)
        labels = labels.to(device)
        pred = model(inputs)
        c_loss = criterion(pred, labels)
        loss.update(c_loss.item())
        acc.update(pred, labels)
    epoch_loss = loss.get()
    epoch_acc = acc.get()
    if epoch_acc > best_acc:
        best_model_wts = copy.deepcopy(model.state_dict())
        local_PATH = '../model_weight/{}-{}-Loss-{:.4f}-Acc-{:.4f}-model.pth' \
            .format(model_name, epoch, epoch_loss, epoch_acc)
        torch.save(best_model_wts, local_PATH)
    return epoch_acc, epoch_loss


def train_model(model, model_name, data_loaders, criterion, optimizer: optimizer, device, scheduler=None,
                num_epochs=25):
    best_acc = 0.0
    for epoch in range(num_epochs):
        train_acc, train_loss = train_epoch(model, data_loaders, optimizer, device, criterion, scheduler)
        valid_acc, valid_loss = valid_epoch(model, data_loaders, device, criterion, model_name, epoch, best_acc)
        if valid_acc > best_acc: best_acc = valid_acc
        scalar_acc = {"train_acc": train_acc, "valid_acc": valid_acc}
        scalar_loss = {"train_loss": valid_loss, "valid_loss": valid_loss}
        scalar_show(writer,scalar_acc,scalar_loss)