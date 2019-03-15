# 损失函数
# HingeEmbeddingLoss
# BCEWithLogitsLoss
# 优化器
# ASGD
# AMSGrad
# 学习率调整方法
# MultiStepLR
# CosineAnnealingLR
import pandas as pd
import torch
from torch.optim.lr_scheduler import MultiStepLR, ReduceLROnPlateau, CosineAnnealingLR
from sklearn.model_selection import train_test_split
import torchvision

from PCam_data_set import PCam_data_set
# from models.pnasnet5large import PNASNet5Large
from models.resnet import resnet18
from trainer import train_model, writer
# from torchvision.models import densenet201
from torchsummary import summary

BATCH_SIZE = 128
NUM_WORKERS = 8
device = 1  # torch.device("cuda:1" if torch.cuda.is_available() else "cpu")

# 加载数据
INPUT_PATH = "/home/arron/文档/notebook/侯正罡/cancer/input"
csv_url = INPUT_PATH + '/train_labels.csv'
data = pd.read_csv(csv_url)
train_path = INPUT_PATH + '/train/'
test_path = INPUT_PATH + '/test/'
data['label'].value_counts()
# 切分训练集和验证集
test_size = 0.1
tr, vd = train_test_split(data, test_size=test_size, random_state=123)
train_set = PCam_data_set(tr, train_path, 'train')
valid_set = PCam_data_set(vd, train_path, 'valid')
train_loader = torch.utils.data.DataLoader(train_set, batch_size=BATCH_SIZE,
                                           shuffle=True, num_workers=NUM_WORKERS)
valid_loader = torch.utils.data.DataLoader(valid_set, batch_size=BATCH_SIZE,
                                           shuffle=False, num_workers=NUM_WORKERS)
dataloaders = {'train': train_loader, 'valid': valid_loader}
# 加载模型
model = resnet18(num_classes=2, pretrained=False)
model_name = 'resnet18'
# models = PNASNet5Large(2)

# 开启多个GPU
# if torch.cuda.device_count() > 1:
#     print("Let's use", torch.cuda.device_count(), "GPUs!")
#     # dim = 0 [30, xxx] -> [10, ...], [10, ...], [10, ...] on 3 GPUs
#     models = nn.DataParallel(models)
# 恢复模型
# PATH = '../weight/resnet50-7-Loss-0.7759 Acc-0.5334-models.pth'
# models.load_state_dict(torch.load(PATH))
# models.eval()

# model可视化

x = torch.rand(1, 3, 32, 32)  # 随便定义一个输入

writer.add_graph(model, x)
summary(model, (3, 32, 32))
# 加载到GPU
model.cuda(device)
# 优化器
params_to_update = model.parameters()
optimizer = torch.optim.Adam(params_to_update, lr=1e-1, amsgrad=True)

# 使用warm_up和余弦退火
scheduler = CosineAnnealingLR(optimizer, T_max=5, eta_min=4e-08)
# scheduler = GradualWarmupScheduler(optimizer, multiplier=8, total_epoch=10,
#                                    after_scheduler=scheduler_cos)
# 损失函数
criterion = torch.nn.CrossEntropyLoss().cuda(device)

# 训练和评估
train_model(model, model_name, dataloaders,
            criterion, optimizer, device, scheduler, num_epochs=120, test_size=test_size)
