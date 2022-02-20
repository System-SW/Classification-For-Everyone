import os
from argparse import ArgumentParser
from typing import Dict, Final
from unicodedata import name

import pytorch_lightning as pl
import torch
import wandb
from pytorch_lightning.callbacks import (
    EarlyStopping,
    LearningRateMonitor,
    ModelCheckpoint,
    TQDMProgressBar,
)
from pytorch_lightning.loggers import WandbLogger
from pytorch_lightning.utilities.seed import seed_everything

import utils
from datamodules import *
from models import *
from transforms import *

DATAMODULE_TABLE: Final[Dict] = {
    "MNIST": MnistDataModule,
    "CIFAR10": CIFAR10DataModule,
    "CIFAR100": CIFAR100DataModule,
}


MODEL_TABLE = {
    "VGG": LitVGG,
}

TRANSFORMS_TABLE = {
    "BASE": BaseTransforms,
}


def hyperparameters():
    parser = ArgumentParser()
    parser = pl.Trainer.add_argparse_args(parser)

    add = parser.add_argument

    ds_candidate = list(DATAMODULE_TABLE.keys())
    model_candidate = list(MODEL_TABLE.keys())
    transfoms_candidate = list(TRANSFORMS_TABLE.keys())

    # experiment hyperparameters
    ## experiment
    add("--seed", type=int, default=9423)
    add("--experiment_name", type=str)
    add("--root_dir", type=str)
    add(
        "--artifact_save_to_logger",
        type=str,
        default="True",
        choices=["True", "False"],
    )

    ## data module/set/transforms
    add("--dataset", type=str, choices=ds_candidate)
    add("--transforms", type=str, choices=transfoms_candidate)
    add("--num_workers", type=int, default=16)
    add("--image_channels", type=int, default=3)
    add("--image_size", type=int)
    add("--batch_size", type=int, default=64)

    ## each model
    add("--model", type=str, choices=model_candidate)
    add("--model_type", type=str)
    add("--num_classes", type=int)
    add("--dropout_rate", type=float, default=0.5)

    ## callbacks
    add("--callbacks_verbose", type=bool, default=True)
    add("--callbacks_monitor", type=str, default="val/acc")
    add("--callbacks_mode", type=str, default="max")
    add("--earlystooping_min_delta", type=float, default=0.1)
    add("--earlystooping_patience", type=float, default=10)

    ## optimizer
    add("--lr", type=float, default=0.1)

    ### SGD
    add("--momentum", type=float, default=0)
    add("--weight_decay", type=float, default=0)
    add("--nesterov", type=float, default=False)

    return parser


def main(args):
    transforms = TRANSFORMS_TABLE[args.transforms.upper()]
    datamodule = DATAMODULE_TABLE[args.dataset.upper()]
    model = MODEL_TABLE[args.model]

    seed_everything(args.seed)

    ######################### BUILD DATAMODULE ##############################
    image_shape = [
        args.image_channels,
        args.image_size,
        args.image_size,
    ]

    train_transforms = transforms(
        image_shape=image_shape,
        train=True,
    )

    test_transforms = transforms(
        image_shape=image_shape,
        train=False,
    )
    datamodule = datamodule(
        root_dir=args.root_dir,
        train_transforms=train_transforms,
        test_transforms=test_transforms,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )
    ############################## MODEL ####################################
    model = model(args)
    model.initialize_weights()

    save_dir = os.path.join(
        args.default_root_dir,
        args.experiment_name,
    )

    ckpt_path = utils.make_checkpoint_dir(
        log_save_dir=os.path.join(save_dir, "ckpt"),
    )

    ############################## LOGGER ###################################
    wandb_logger = WandbLogger(
        project=args.experiment_name,
        save_dir=save_dir,
        log_model="all",
    )
    wandb_logger.watch(model, log="all", log_freq=args.log_every_n_steps)

    ############################## CALLBACKS ################################
    callbacks = [
        TQDMProgressBar(refresh_rate=5),
        LearningRateMonitor(logging_interval="epoch"),
        EarlyStopping(
            monitor=args.callbacks_monitor,
            mode=args.callbacks_mode,
            min_delta=args.earlystooping_min_delta,
            patience=args.max_epochs // 2,
            verbose=args.callbacks_verbose,
        ),
        ModelCheckpoint(
            monitor=args.callbacks_monitor,
            mode=args.callbacks_mode,
            dirpath=ckpt_path,
            filename="[{epoch}]-[{step}]-[{val/acc:.2f}]",
            save_top_k=5,
            save_last=True,
            verbose=args.callbacks_verbose,
        ),
    ]

    ############################## TRAIN SETTING ############################
    trainer = pl.Trainer.from_argparse_args(
        args,
        logger=wandb_logger,
        callbacks=callbacks,
    )

    ############################# TRAIN START ###############################
    # trainer.fit(model, datamodule=datamodule)
    wandb_logger.experiment.unwatch(model)
    ############################# TEST  START ###############################
    test_info = trainer.test(model, datamodule=datamodule)

    return test_info


if __name__ == "__main__":
    parser = hyperparameters()
    args = pl.Trainer.parse_argparser(parser.parse_args())
    info = main(args)
