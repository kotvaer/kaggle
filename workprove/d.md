# 训练模型
model.train(
    data='/kaggle/input/weld888/datasets/Data/data.yaml',
    epochs=300,        # 增加训练轮次
    batch=10,          # 适当增加批量大小
    imgsz=640,         # 图像尺寸保持不变
    lr0=0.0005,        # 降低初始学习率
    lrf=0.05,          # 最终学习率因子，允许学习率下降更慢
    patience=50,       # 增加早停耐心值
    amp=True,          # 混合精度训练，保持不变，有助于效率
    multi_scale=True,  # 多尺度训练，保持不变，对小目标有利
    workers=8,         # 增加数据加载器工作进程数 (如果CPU资源允许)
    optimizer='AdamW', # 尝试AdamW优化器，通常效果更好
    cache=True,      # 缓存数据，加快读取速度
)