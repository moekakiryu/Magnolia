import sys
import warnings

class IO:
    # this should be a mainly static class
    stdout = sys.stdout
    stderr = sys.stderr
    
    @staticmethod
    def raise_err(err_type, err_msg):
        if isinstance(err_type(), Warning):
            warnings.warn(err_msg, err_type)
        elif isinstance(err_type(), Exception):
            raise err_type(err_msg)