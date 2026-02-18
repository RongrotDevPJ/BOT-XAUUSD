from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame):
        """
        Analyze the market data and return signal and details.
        Returns:
            signal (str): "BUY", "SELL", "WAIT", etc.
            status_detail (str): Description of the signal status.
            extra_data (dict): Dictionary containing additional data for logging or display.
        """
        pass
