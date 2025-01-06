from src import FileSystemWatcher, StationReport, JointReport, read_bulletin

if __name__ == '__main__':
    # watch = FileSystemWatcher('ftpdata/')
    # watch.main_loop()
    # a = StationReport.from_file('ftpdata/SI325.15')
    # b = StationReport.from_file('ftpdata/SM376.12')
    # print(a)
    # print(b)


    c = read_bulletin('ftpdata/WX.06')
    print(c)