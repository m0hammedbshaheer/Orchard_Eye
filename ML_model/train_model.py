from ultralytics import YOLO
import os

def main():
    # Load a pretrained YOLOv8 model (nano version for speed)
    print("Loading YOLOv8 nano model...")
    model = YOLO("yolov8n.pt")
    
    # Define absolute path to data.yaml
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_yaml_path = os.path.join(base_dir, "Training_databse", "data.yaml")
    
    print(f"Starting training with dataset: {data_yaml_path}")
    # Train the model
    results = model.train(
        data=data_yaml_path,
        epochs=10,  # Limits epochs for quick proof-of-concept
        imgsz=640,
        batch=16,
        project=os.path.join(base_dir, "RaspberryPi_reciver", "ArticicialIntelligence-Powered-pheromone-trap"),
        name="pest_model", # Name of the folder where results will be saved
        exist_ok=True # Overwrite existing if run multiple times
    )
    print("Training complete! Model saved to RaspberryPi_reciver/ArticicialIntelligence-Powered-pheromone-trap/pest_model/weights/best.pt")

if __name__ == "__main__":
    main()
