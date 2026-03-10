from l1_microstructure.artifacts import ArtifactStore
from l1_microstructure.calibration import StateCalibrator
from l1_microstructure.datasets import TransitionDatasetBuilder
from l1_microstructure.ingest import MarketDataSource
from l1_microstructure.live import PaperTradingRunner
from l1_microstructure.monitoring import MonitoringSink
from l1_microstructure.replay import ReplayController
from l1_microstructure.training import TransitionTrainer
from l1_microstructure.validation import ValidationHarness


def test_successor_contracts_are_importable() -> None:
    contracts = [
        ArtifactStore,
        MarketDataSource,
        MonitoringSink,
        PaperTradingRunner,
        ReplayController,
        StateCalibrator,
        TransitionDatasetBuilder,
        TransitionTrainer,
        ValidationHarness,
    ]

    assert all(contract is not None for contract in contracts)