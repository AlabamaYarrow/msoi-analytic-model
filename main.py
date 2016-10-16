import sys
from math import pow

from PyQt5.QtWidgets import (QAbstractItemView, QApplication,
                             QDialog, QTableWidgetItem, QMessageBox)

from ui_dialog import Ui_MainWindow


class UserInput:
    def __init__(self, n, to, tp, tk1, tk2, c, tpr, m, tdi, p, k1, k2, delta):
        self.n = int(n)
        self.tp = float(tp)
        self.to = float(to)
        self.tk1 = float(tk1)
        self.tk2 = float(tk2)
        self.c = int(c)
        self.tpr = float(tpr)
        self.m = int(m)
        self.tdi = float(tdi)
        self.p = float(p)
        self.k1 = float(k1)
        self.k2 = float(k2)
        self.delta = float(delta)
        self.tk = (self.tk1 + self.tk2) / 2
        self.pi = 1 / self.m
        if any([self.n < 0, self.tp < 0, self.to < 0, self.tk1 < 0,
                self.tk2 < 0, self.c < 0, self.tpr < 0, self.m < 0,
                self.tdi < 0, self.p < 0, self.p > 1, self.k2 < 10, self.k2 > 100000,
                self.k1 > 0.999995, self.k1 < 0.9, self.delta < 0.000001,
                self.delta > 0.9]):
            raise ValueError


class MainWindow(QDialog, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.input = None
        self.output = {}
        self.setupUi(self)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.calc_pushButton.clicked.connect(self.on_start_calculation)

    def show_error(self, *args):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Неверные входные параметры")
        msg.setInformativeText("Проверьте введенные значения")
        msg.setWindowTitle("Ошибка ввода")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def on_start_calculation(self):
        try:
            self.input = UserInput(
                self.n_lineEdit.text(), self.to_lineEdit.text(),
                self.tp_lineEdit.text(), self.tk1_lineEdit.text(),
                self.tk2_lineEdit.text(), self.c_lineEdit.text(),
                self.tpr_lineEdit.text(), self.m_lineEdit.text(),
                self.tdi_lineEdit.text(), self.p_lineEdit.text(),
                self.k1_lineEdit.text(), self.k2_lineEdit.text(),
                self.delta_lineEdit.text()
            )
        except ValueError:
            self.show_error()
            self.input = None
        self.calculate()
        self.input = None

    def calculate(self):
        self.output = {}
        self.set_output_values()
        self.fill_table()
        self.tabWidget.setCurrentIndex(2)

    def fill_table(self):
        table_column = [self.output['ro_PC'], self.output['ro_user'], self.output['busy_PC_avg'],
                        self.output['ro_channel'], self.output['ro_pr'], self.output['ro_di'],
                        self.output['t_cycle'], self.output['t_react'], self.output['lambda_f1'],
                        self.output['lambda_f_final'], self.output['iterations']]
        for i in range(0, self.tableWidget.rowCount()):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(table_column[i], 5))))

    def set_output_values(self):
        beta = 1 / (1 - self.input.p)
        self.output['beta'] = beta

        self.set_labmda(beta)

        lambda_ = self.input.n / self.output['t_cycle']
        # загрузка процессора
        self.output['ro_pr'] = beta * lambda_ * self.input.tpr / self.input.c
        # загрузка рабочей станции
        self.output['ro_PC'] = (self.input.to + self.input.tp) / self.output['t_cycle']
        # среднее число работающих машин
        self.output['busy_PC_avg'] = self.output['ro_PC'] * self.input.n
        # загрузка пользователя
        self.output['ro_user'] = self.input.tp / self.output['t_cycle']
        # загрузка канала
        self.output['ro_channel'] = 2 * lambda_ * self.input.tk
        # загрузка i-го диска
        self.output['ro_di'] = beta * lambda_ * self.input.tdi * self.input.pi

    def set_labmda(self, beta):
        lambda_args = [
            1 / (2 * self.input.tk),
            self.input.c / (beta * self.input.tpr),
            1 / (beta * self.input.pi * self.input.tdi)
        ]
        # начальная интенсивность входного потока
        lambda_f1 = self.input.k1 * min(lambda_args) * (self.input.n - 1) / self.input.n
        self.output['lambda_f1'] = lambda_f1
        tk_avg = self.get_tk_avg(lambda_f1)
        tpr_avg = self.get_tpr_avg(beta, lambda_f1)
        td_avg = self.get_td_avg(beta, lambda_f1)
        lambda_f = (self.input.n - 1) / (self.input.to + self.input.tp + tk_avg + tpr_avg + td_avg)
        iterations = 0
        while (abs(lambda_f1 - lambda_f) / lambda_f) >= self.input.delta:
            delta1 = (lambda_f1 - lambda_f) / self.input.k2
            lambda_f1 -= delta1
            tk_avg = self.get_tk_avg(lambda_f1)
            tpr_avg = self.get_tpr_avg(beta, lambda_f1)
            td_avg = self.get_td_avg(beta, lambda_f1)
            lambda_f = (self.input.n - 1) / (self.input.to + self.input.tp + tk_avg + tpr_avg + td_avg)
            iterations += 1
        # число итераций
        self.output['iterations'] = iterations
        # конечное значение интенсивности
        self.output['lambda_f_final'] = lambda_f
        # время цикла системы
        self.output['t_cycle'] = self.input.to + self.input.tp + tk_avg + tpr_avg + td_avg
        # время реакции системы
        self.output['t_react'] = tk_avg + tpr_avg + td_avg

    def get_tk_avg(self, lambda_f1):
        return 2 * self.input.tk / (1 - 2 * lambda_f1 * self.input.tk)

    def get_tpr_avg(self, beta, lambda_f1):
        return beta * self.input.tpr / (1 - pow((beta * lambda_f1 * self.input.tpr) / self.input.c, self.input.c))

    def get_td_avg(self, beta, lambda_f1):
        return beta * self.input.tdi / (1 - beta * self.input.pi * lambda_f1 * self.input.tdi)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
