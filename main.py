import sys
from math import pow

from PyQt5.QtWidgets import (QAbstractItemView, QApplication,
                             QDialog, QTableWidgetItem, QMessageBox)

from ui_dialog import Ui_MainWindow


class UserInput:
    def __init__(self, n, to, tp, tk1, tk2, c, tpr, m, tdi, p, k1, k2, delta):
        self.n = n
        self.tp = tp
        self.to = to
        self.tk1 = tk1
        self.tk2 = tk2
        self.c = c
        self.tpr = tpr
        self.m = m
        self.tdi = tdi
        self.p = p
        self.k1 = k1
        self.k2 = k2
        self.delta = delta
        self.tk = 0
        self.pi = 0

    def is_valid(self):
        try:
            self.n = int(self.n)
            self.tp = float(self.tp)
            self.to = float(self.to)
            self.tk1 = float(self.tk1)
            self.tk2 = float(self.tk2)
            self.c = int(self.c)
            self.tpr = float(self.tpr)
            self.m = int(self.m)
            self.tdi = float(self.tdi)
            self.p = float(self.p)
            self.k1 = float(self.k1)
            self.k2 = float(self.k2)
            self.delta = float(self.delta)
            self.tk = (self.tk1 + self.tk2) / 2
            self.pi = 1 / self.m
            if any([self.n < 0, self.tp < 0, self.to < 0, self.tk1 < 0,
                    self.tk2 < 0, self.c < 0, self.tpr < 0, self.m < 0,
                    self.tdi < 0, self.p < 0, self.p > 1, self.k2 < 10, self.k2 > 100000,
                    self.k1 > 0.999995, self.k1 < 0.9, self.delta < 0.000001,
                    self.delta > 0.9]):
                raise ValueError
        except ValueError:
            return False
        return True


class MainWindow(QDialog, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.input = None
        self.output = {}
        self.setupUi(self)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.calc_pushButton.clicked.connect(self.start_calculation)

    def show_error(self, *args):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Неверные входные параметры")
        msg.setInformativeText("Проверьте введенные значения")
        msg.setWindowTitle("Ошибка ввода")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def start_calculation(self):
        self.input = UserInput(
            self.n_lineEdit.text(), self.to_lineEdit.text(),
            self.tp_lineEdit.text(), self.tk1_lineEdit.text(),
            self.tk2_lineEdit.text(), self.c_lineEdit.text(),
            self.tpr_lineEdit.text(), self.m_lineEdit.text(),
            self.tdi_lineEdit.text(), self.p_lineEdit.text(),
            self.k1_lineEdit.text(), self.k2_lineEdit.text(),
            self.delta_lineEdit.text()
        )
        if not self.input.is_valid():
            self.show_error()
        else:
            self.calculate()
        self.input = None

    def calculate(self):
        self.output = {}

        self.set_output_values()

        table_column = [self.output['ro_PC'], self.output['ro_user'], self.output['busy_PC_avg'],
                        self.output['ro_channel'], self.output['ro_pr'], self.output['ro_di'],
                        self.output['t_cycle'], self.output['t_react'], self.output['lambda_f1'],
                        self.output['lambda_f_final'], self.output['iterations']]
        for i in range(0, self.tableWidget.rowCount()):
            self.tableWidget.setItem(i, 0,  QTableWidgetItem(str(round(table_column[i], 5))))

        self.tabWidget.setCurrentIndex(2)

    def set_output_values(self):
        beta = 1 / (1 - self.input.p)
        self.output['beta'] = beta

        lambda_args = [
            1 / (2 * self.input.tk),
            self.input.c / (beta * self.input.tpr),
            1 / (beta * self.input.pi * self.input.tdi)
        ]

        # интесивность входного потока
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

        self.output['lambda_f_final'] = lambda_f
        t_cycle = self.input.to + self.input.tp + tk_avg + tpr_avg + td_avg
        self.output['t_cycle'] = t_cycle
        self.output['t_react'] = tk_avg + tpr_avg + td_avg

        self.output['iterations'] = iterations

        lambda_ = self.input.n / t_cycle
        # загрузка процессора
        self.output['ro_pr'] = beta * lambda_ * self.input.tpr / self.input.c
        # загрузка рабочей станции
        self.output['ro_PC'] = (self.input.to + self.input.tp) / t_cycle
        # среднее число работающих машин
        self.output['busy_PC_avg'] = self.output['ro_PC'] * self.input.n
        # загрузка пользователя
        self.output['ro_user'] = self.input.tp / t_cycle
        # загрузка канала
        self.output['ro_channel'] = 2 * lambda_ * self.input.tk
        # загрузка i-го диска
        self.output['ro_di'] = beta * lambda_ * self.input.tdi * self.input.pi

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
