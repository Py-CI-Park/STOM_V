import sys
import random
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QAbstractItemView, QTableWidgetItem, QHeaderView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('STOM')
        self.geometry().center()
        self.resize(500, 300)

        columns = ['1', '2', '3', '4', '5']
        self.tableWidget = QTableWidget(self)
        self.tableWidget.verticalHeader().setDefaultSectionSize(26)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setSelectionMode(QAbstractItemView.NoSelection)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget.setColumnCount(len(columns))
        self.tableWidget.setRowCount(10)
        self.tableWidget.setHorizontalHeaderLabels(columns)
        self.tableWidget.setGeometry(5, 5, 490, 290)

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.table_auto_col_change)
        self.qtimer.start()

    def table_auto_col_change(self):
        data_list1 = list(np.random.rand(10))
        data_list2 = list(np.random.rand(10))
        data_list3 = list(np.random.rand(10))
        data_list4 = list(np.random.rand(10))
        data_list5 = list(np.random.rand(10))
        df = pd.DataFrame({'1': data_list1, '2': data_list2, '3': data_list3, '4': data_list4, '5': data_list5})

        sequence = [1, 3, 5, 7, 9]
        random.shuffle(sequence)

        df['1'] = df['1'].round(sequence[0])
        df['2'] = df['2'].round(sequence[1])
        df['3'] = df['3'].round(sequence[2])
        df['4'] = df['4'].round(sequence[3])
        df['5'] = df['5'].round(sequence[4])

        arry = df.values
        for i, index in enumerate(df.index):
            for j, column in enumerate(df.columns):
                item = QTableWidgetItem(str(arry[i, j]))
                item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
                self.tableWidget.setItem(i, j, item)

        header = self.tableWidget.horizontalHeader()
        twidth = header.width()
        width = []
        for column in range(header.count()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
            width.append(header.sectionSize(column))

        wfactor = twidth / sum(width)
        for column in range(header.count()):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
            header.resizeSection(column, int(width[column] * wfactor))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    app.exec_()
