from src import FileSystemWatcher

if __name__ == '__main__':
    watch = FileSystemWatcher('.')
    watch.main_loop()