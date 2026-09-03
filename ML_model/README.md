# ArtificialIntelligence-Powered-Pheromone-Trap
Pheromone Trap integrated with IoT devices (Raspberry Pi and ESP-32) and artificial intelligence technology to estimate live count of insects, helping in early detection and estimation of infestation, subsequently helping farmers estimate pesticide spray, preventing pesticide resistance and overuse of pesticides.
# Contributors
Mohammed Shaheer — Embedded Systems & AI Lead. Architected and wired up all the hardware magic — from circuit design to getting the electrons to behave. Also co-developed the computer vision model and handled data augmentation, turning raw trap images into intelligent insect predictions.
Mosin Mushtaq — Full-Stack & IoT Integration Lead. Built the frontend, backend, and engineered the seamless bridge between the ESP32, Raspberry Pi, and the cloud.
# Technology used
microcontrollers and microprocessors:
Esp32 - capture images and send it to cloud server
rapberrypi - download,store and process the data then publish results on the website skuast.store.py
Powersupply: 
5v Battery to give power supple to esp32 which lasts more than 6 months
solar power to extend batterylife
Casing
3D printed custom casing for the project
## AI & Server Workflow
Our implementation handles real-time data flow from capturing images to rendering dynamic analytics.

### Step-by-Step Logic
1. **Image Capture**: The ESP32 triggers the camera, captures the state of the pheromone trap, and sends a `multipart/form-data` POST request to the Raspberry Pi Flask server (`/upload`).
2. **Dynamic Inference**: The Flask Backend catches the image and instantly spins up a customized **YOLOv8** Object Detection Model. The AI scans the image, drawing bounding boxes specifically targeting custom trained classes (Insects, dust, holes).
3. **Difference Calculation**: To ensure we don't double count, the backend (`services/data_service.py`) checks the local `logs.csv` database for the specific trap's last image count. It subtracts the previous count from the current YOLO prediction to find the **hourly difference** (new pests captured).
4. **Data Aggregation**: The new absolute count, image path, timestamp, and difference are physically appended to the system log, preserving historical timeline data without relying on external cloud databases.
5. **Dashboard Visualization**: The image (now overlaid with YOLO bounding boxes) is rendered and saved into the public `/static/img/gallery/` folder where the web-app automatically updates the user dashboard interface with the new live capture and regional trend lines!

### Why YOLOv8 is Preferred
We chose **Ultralytics YOLOv8** over traditional CNN classifiers or cloud APIs because:
* **Edge Optimized**: YOLOv8 is highly optimized for Edge Devices (like Raspberry Pis), performing rapid inferences via CPU without requiring a massive dedicated GPU.
* **Granular Object Detection**: Instead of just outputting "15 bugs", YOLO provides explicit *localization* coordinates, highlighting *where* the bugs actually are. This provides concrete visual proof to farmers navigating the dashboard!
* **Fast Fine-Tuning**: Developing custom classes (filtering out "dust" and "holes" to only focus on actual insects) requires minimal data to achieve state-of-the-art `mAP` metrics.
