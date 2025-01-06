from src import read_bulletin, read_station_report

if __name__ == '__main__':
    # watch = FileSystemWatcher('ftpdata/')
    # watch.main_loop()
    a = read_station_report('ftpdata/SI325.15')
    b = read_station_report('ftpdata/SM376.12')
    print(a)
    print(b)


    c = read_bulletin('ftpdata/WX.06')
    print(c)