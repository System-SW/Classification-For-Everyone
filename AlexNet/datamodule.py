from typing import Optional
import pytorch_lightning as pl
from torch.utils.data import DataLoader, random_split
from torchvision import transforms
from torchvision.datasets import CIFAR10


class CIFAR10DataModule(pl.LightningDataModule):
    def __init__(
            self,
            data_dir: str = './data',
            image_size: int = 256,
            batch_size: int = 32,
    ):
        super().__init__()
        self.save_hyperparameters()

        self.train_transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomVerticalFlip(p=0.5),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[x / 255.0 for x in [125.3, 123.0, 113.9]],
                    std=[x / 255.0 for x in [63.0, 62.1, 66.7]],
                ),
            ]
        )

        self.test_transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[x / 255.0 for x in [125.3, 123.0, 113.9]],
                    std=[x / 255.0 for x in [63.0, 62.1, 66.7]],
                ),
            ]
        )
        self.dataset = CIFAR10

    def prepare_data(self) -> None:
        """Dataset downlaod"""
        self.dataset(self.hparams.data_dir, train=True, download=True)
        self.dataset(self.hparams.data_dir, train=False, download=True)

    def setup(self, stage: Optional[str] = None) -> None:
        # Assign train/val datasets for use in dataloaders
        if stage == 'fit' or stage is None:
            dataset = self.dataset(
                self.hparams.data_dir,
                train=True,
                transform=self.train_transform,
            )

            train_ds_size = int(len(dataset) * 0.8)
            val_ds_size = len(dataset) - train_ds_size

            self.train_ds, self.val_ds = random_split(
                dataset,
                [train_ds_size, val_ds_size]
            )

        # Assign test dataset for use in dataloader(s)
        if stage == 'test' or stage is None:
            self.test_ds = self.dataset(
                self.hparams.data_dir,
                train=False,
                transform=self.test_transform
            )

    def train_dataloader(self) -> DataLoader:
        return DataLoader(
            self.train_ds,
            batch_size=self.hparams.batch_size,
            shuffle=True,
            num_workers=0,
        )

    def val_dataloader(self) -> DataLoader:
        return DataLoader(
            self.val_ds,
            batch_size=self.hparams.batch_size,
            shuffle=False,
            num_workers=0,
        )

    def test_dataloader(self) -> DataLoader:
        return DataLoader(
            self.test_ds,
            batch_size=self.hparams.batch_size,
            shuffle=False,
            num_workers=0,
        )