# 训练可视化tensorboardX
# LR:add_scalar
# acc,loss:add_scalars
# 权重变化：add_histogram
# 图模型结构：add_graph
# 特征降维：add_embedding
# 输出结果混淆矩阵：混淆矩阵
import os

import torch
import time
import copy
from tensorboardX import SummaryWriter
from torch.optim import optimizer
from tqdm import tqdm
import pandas as pd
from collections import OrderedDict

START_TIME = time.strftime("%Y-%m-%d--%H:%M:%S", time.localtime())

writer = SummaryWriter(os.path.join('logs','tensorBoardX',START_TIME))


class Acc:
    def __init__(self, name):
        self.name = name
        self.correct = 0
        self.sample = 0
        self.acc_hist = []

    def reset(self):
        self.correct = 0
        self.sample = 0

    def update(self, pred, label, time):
        pred = torch.argmax(pred, 1)
        correct = pred.size(0) - (pred ^ label).sum().item()
        sample = pred.size(0)
        acc = correct / sample
        writer.add_scalars("acc", {self.name: acc}, time)
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

    def update(self, loss, time):
        writer.add_scalars("loss", {self.name: loss}, time)
        self.loss += loss
        self.sample += 1

    def get(self):
        return self.loss / self.sample


class LearningRate:
    def __init__(self):
        self.LR_hist = []


# def scalar_show(acc=None, loss=None, **kwargs):
#     if acc:
#         writer.add_scalars("acc", acc)
#     if loss:
#         writer.add_scalars("loss", loss)
#     for key, item in kwargs:
#         writer.add_scalar(key, item)


def logs_toCSV(train_loss=None,train_acc=None,valid_loss=None,valid_acc=None,header=False):
    logs = OrderedDict({'train_loss': [train_loss], "train_acc": [train_acc], 'valid_loss': [valid_loss], 'valid_acc': [valid_acc]})
    df = pd.DataFrame(logs)
    df.to_csv(f"logs/csv/{START_TIME}.csv",mode='a', header=header,index=False)


def train_epoch(model, data_loaders, optimizer, device, criterion, epoch, scheduler=None):
    acc = Acc("train_batch_acc")
    loss = Loss("train_batch_loss")
    model.train()
    data_size = len(data_loaders["train"])
    i = 0

    with torch.set_grad_enabled(True):
        for inputs, labels in data_loaders["train"]:
            optimizer.zero_grad()
            inputs = inputs.cuda(device)
            labels = labels.cuda(device)
            pred = model(inputs)
            c_loss = criterion(pred, labels)
            c_loss.backward()
            optimizer.step()
            loss.update(c_loss.item(), epoch * data_size + i)
            acc.update(pred, labels, epoch * data_size + i)
            i += 1
        writer.add_scalar("learningRate", optimizer.param_groups[0]['lr'], (epoch + 1) * data_size)
        epoch_loss = loss.get()
        epoch_acc = acc.get()
        if scheduler:
            if type(scheduler) == torch.optim.lr_scheduler.ReduceLROnPlateau:
                pass
            else:
                scheduler.step()
    return epoch_acc, epoch_loss


def valid_epoch(model, data_loaders, device, criterion, model_name, epoch, best_acc, gap):
    acc = Acc("valid_batch_acc")
    loss = Loss("valid_batch_loss")
    model.eval()
    data_size = len(data_loaders["valid"])
    i = 0
    for inputs, labels in data_loaders["valid"]:
        inputs = inputs.cuda(device)
        labels = labels.cuda(device)
        pred = model(inputs)
        c_loss = criterion(pred, labels)
        loss.update(c_loss.item(), gap * (epoch * data_size + i))
        acc.update(pred, labels, gap * (epoch * data_size + i))
        i += 1
    epoch_loss = loss.get()
    epoch_acc = acc.get()
    if epoch_acc > best_acc:
        local_path = "models_weight/MyWeight/" + START_TIME
        if not os.path.exists(local_path):
            os.makedirs(local_path)
        file_name = '{}--{}--{}--Loss--{:.4f}--Acc--{:.4f}.pth' \
            .format(time.strftime("%Y-%m-%d--%H:%M:%S", time.localtime()),
                    model_name, epoch, epoch_loss, epoch_acc)
        torch.save(copy.deepcopy(model.state_dict()), os.path.join(local_path, file_name))
        print(f"save: {os.path.join(local_path, file_name)}")
    return epoch_acc, epoch_loss


def train_model(model, model_name, data_loaders, criterion, optimizer: optimizer, device, scheduler=None,
                test_size=0.1, num_epochs=None):
    if num_epochs is None:
        num_epochs = [0, 25]
    best_acc = 0.0
    gap = int((1 - test_size) * 10)

    for epoch in range(num_epochs[0], num_epochs[1]):
        start_time = time.time()
        train_acc, train_loss = train_epoch(model, data_loaders, optimizer, device, criterion,
                                            epoch, scheduler=scheduler)
        valid_acc, valid_loss = valid_epoch(model, data_loaders, device, criterion, model_name,
                                            epoch, best_acc, gap)
        if type(scheduler) == torch.optim.lr_scheduler.ReduceLROnPlateau:
            scheduler.step(valid_loss)
        time_elapsed = time.time() - start_time
        last_time = "{:.0f}m {:.0f}s".format(time_elapsed // 60, time_elapsed % 60)
        if valid_acc > best_acc:
            best_acc = valid_acc
        log = "epoch:{:4}--train_loss:{:4f}--train_acc:{:4f}--valid_loss:{:4f}--valid_acc:{:4f}--time:{}" \
            .format(epoch, train_loss, train_acc, valid_loss, valid_acc, last_time)
        print(log)
        logs_toCSV(train_loss,train_acc,valid_loss,valid_acc)

if __name__ == '__main__':
    logs_toCSV(header=True)