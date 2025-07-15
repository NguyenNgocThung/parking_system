import os
import sys
from gui.app import App
from config import UI_CONFIG  
from database.database_manager import DatabaseManager
from my_parking.camera import get_camera_manager

def main():
    db_manager = DatabaseManager()
    db_manager.initialize_database()

    camera_manager = get_camera_manager()
    camera_manager.initialize_all_cameras() 

    app = App()
    try:
        app.mainloop()
    finally:
        camera_manager.stop_all_cameras()

if __name__ == "__main__":
    main()