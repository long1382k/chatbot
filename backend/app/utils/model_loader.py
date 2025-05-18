import yaml
from app.config import MODEL_CONFIG_PATH

def get_model_list():
    with open(MODEL_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def load_models_by_type(model_type: str):
    data = get_model_list()
    return data.get(model_type, [])
def find_model(model_name: str):
    """
    Tìm model theo model_name, trả về thông tin model và loại (local hoặc remote)
    """
    data = get_model_list()
    for model_type in ["remote", "local"]:
        for model in data.get(model_type, []):
            if model["model_name"] == model_name:
                return {"type": model_type, **model}
    return None
