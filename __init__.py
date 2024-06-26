import os
import folder_paths
import numpy as np
import torch
from comfy.utils import ProgressBar
from .utilities import Engine

ENGINE_DIR = os.path.join(folder_paths.models_dir,"tensorrt/upscaler")

class UpscalerTensorrt:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": { 
                "images": ("IMAGE",),
                "engine": (os.listdir(ENGINE_DIR),),
            }
        }
    RETURN_NAMES = ("IMAGE",)
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "main"
    CATEGORY = "tensorrt"

    def main(self, images, engine):
        images = images.permute(0, 3, 1, 2) # B,C,W,H
        B,C,W,H = images.shape
        shape_dict = {
            "input": {"shape": (1, 3, W, H)},
            "output": {"shape": (1, 3, W*4, H*4)},
        }
        # setup tensorrt engine
        engine = Engine(os.path.join(ENGINE_DIR,engine))
        engine.load()
        engine.activate()
        engine.allocate_buffers(shape_dict=shape_dict)
        cudaStream = torch.cuda.current_stream().cuda_stream

        pbar = ProgressBar(B)
        images_list = list(torch.split(images, split_size_or_sections=1))

        upscaled_frames = []

        for img in images_list:
            result = engine.infer({"input": img},cudaStream)

            output = result['output'].cpu().numpy().squeeze(0)
            output = np.transpose(output, (1, 2, 0))
            output = np.clip(255.0 * output, 0, 255).astype(np.uint8)

            upscaled_frames.append(output)
            pbar.update(1)
        
        upscaled_frames_np = np.array(upscaled_frames).astype(np.float32) / 255.0
        return (torch.from_numpy(upscaled_frames_np),)


NODE_CLASS_MAPPINGS = { 
    "UpscalerTensorrt" : UpscalerTensorrt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
     "UpscalerTensorrt" : "Upscaler Tensorrt",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']