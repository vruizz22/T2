from gurobipy import GRB
import gurobipy as gp
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem)
import sys


def leer_archivo(archivo: str) -> list:
    with open(archivo, 'r') as file:
        return file.readlines()


class Modelo:

    def __init__(self) -> None:
        '''
        Leer los archivos
        y verificar que no esten vacios
        '''

        archivos = {
            'capacidad_saco': 'capacidad_por_saco.csv',
            'costo_saco': 'costo_saco.csv',
            'tiempo_demora': 'tiempo_demora.csv',
            'kilos_fruta': 'kilos_fruta.csv',
            'precio_venta': 'precio_venta.csv',
            'capital': 'capital_inicial.csv',
            'cuadrantes': 'cantidad_cuadrantes.csv'
        }
        lineas = {key: leer_archivo(value) for key, value in archivos.items()}

        # Verificar que los archivos no estén vacíos
        assert all(len(value) > 0 for value in lineas.values()
                   ), "Algun archivo está vacío. Revisa los archivos :)"
        # Verificar que capital y cuadrantes sean un solo valor
        for key in ['capital', 'cuadrantes']:
            for line in lineas[key]:
                assert len(line.strip().split(',')
                           ) == 1, f"El archivo {key} no tiene un solo valor"
        self.capacidad_saco = [
            int(line.strip()) for line in lineas['capacidad_saco']
        ]
        self.costo_saco = [
            list(map(int, line.strip().split(','))) for line in lineas['costo_saco']
        ]
        self.tiempo_demora = [
            int(line.strip()) for line in lineas['tiempo_demora']
        ]
        self.kilos_fruta = [
            int(line.strip()) for line in lineas['kilos_fruta']
        ]
        self.precio_venta = [
            list(map(int, line.strip().split(','))) for line in lineas['precio_venta']
        ]
        self.capital = int(lineas['capital'][0].strip())
        self.cuadrantes = int(lineas['cuadrantes'][0].strip())

        # Cardinalidad de los conjuntos
        self.K = range(1, self.cuadrantes + 1)
        self.J = range(1, len(self.capacidad_saco) + 1)
        self.T = range(1, len(self.costo_saco[0]) + 1)

        # Archivos que tienen dimensiones J x T
        archivos_jt = {
            'costo_saco': self.costo_saco,
            'precio_venta': self.precio_venta
        }
        # Archivos que tienen dimensiones J
        archivos = {
            'capacidad_saco': self.capacidad_saco,
            'tiempo_demora': self.tiempo_demora,
            'kilos_fruta': self.kilos_fruta,
        }

        # Verificar que todos los archivos tengan las mismas dimensiones
        assert all(len(value) == len(self.J) for value in archivos.values(
        )), "Los archivos no tienen la misma cantidad de elementos"
        assert all(len(value[0]) == len(self.T) for value in archivos_jt.values(
        )), "Los archivos no tienen la misma cantidad de elementos"

        # Parametros
        self.a_j = {
            j: a_j for j, a_j in zip(self.J, self.capacidad_saco)
        }
        self.c_jt = {
            (j, t): c_jt for j, costo_semilla in zip(self.J, self.costo_saco)
            for t, c_jt in zip(self.T, costo_semilla)
        }
        self.O_j = {
            j: O_j for j, O_j in zip(self.J, self.tiempo_demora)
        }
        self.l_j = {
            j: l_j for j, l_j in zip(self.J, self.kilos_fruta)
        }
        self.B_jt = {
            (j, t): B_jt for j, precio_semilla in zip(self.J, self.precio_venta)
            for t, B_jt in zip(self.T, precio_semilla)
        }

    def implementar_modelo(self) -> tuple:
        # Implementando el modelo
        model = gp.Model()

        '''
        Variables de decision
        x_jkt: 1 si se siembra la semilla j en el cuadrante k en el tiempo t,
        0 en otro caso
        y_jkt: 1 si existe la semilla j en el cuadrante k en el tiempo t,
        0 en otro caso
        I_t: Cantidad de dienero en el tiempo t
        U_jt: Cantidad de semillas tipo j al termino del periodo t
        W_jt: Cantidad de sacos semillas tipo j a comprar en el periodo t
        '''

        x_jkt = model.addVars(self.J, self.K, self.T,
                              vtype=GRB.BINARY, name="x_jkt")
        y_jkt = model.addVars(self.J, self.K, self.T,
                              vtype=GRB.BINARY, name="y_jkt")
        I_t = model.addVars(self.T, vtype=GRB.CONTINUOUS, name="I_t")
        U_jt = model.addVars(self.J, self.T, vtype=GRB.INTEGER, name="U_jt")
        W_jt = model.addVars(self.J, self.T, vtype=GRB.INTEGER, name="W_jt")

        # Agregamos las variables al modelo
        model.update()

        '''
        Restricciones
        1. Activación de sembrado
        2. Solo 1 sembrado por cuadrante
        3. Inventario de dinero
        4. Condicion borde inventario dinero
        5. Inventario de semillas
        6. Condición borde semillas
        7. Terminar cosecha antes de volver a cosechar
        '''
        #
        model.addConstrs(
            (sum(y_jkt[j, k, l] for l in range(t, min(t + self.O_j[j] - 1, max(self.T)) + 1))
             >= self.O_j[j] * x_jkt[j, k, t]
             for j in self.J for k in self.K for t in self.T),
            name="Activacion_sembrado"
        )

        model.addConstrs(
            (sum(y_jkt[j, k, t] for j in self.J) <= 1
             for k in self.K for t in self.T),
            name="Solo_un_sembrado"
        )

        model.addConstrs(
            (I_t[t] == I_t[t - 1] - sum(W_jt[j, t] * self.c_jt[j, t] for j in self.J) +
             sum(x_jkt[j, k, t - self.O_j[j]] * self.l_j[j] *
                 self.B_jt[(j, t)] for j in self.J if t - self.O_j[j] >= 1 for k in self.K)
             for t in self.T if t >= 2),
            name="Inventario_dinero"
        )

        model.addConstr(
            I_t[1] == self.capital -
            sum(self.c_jt[(j, 1)] * W_jt[j, 1] for j in self.J),
            name="Condicion_borde_dinero"
        )

        model.addConstrs(
            (U_jt[j, t] == U_jt[j, t - 1] + self.a_j[j] * W_jt[j, t] -
             sum(x_jkt[j, k, t] for k in self.K)
             for j in self.J for t in self.T if t >= 2),
            name="Inventario_semillas"
        )

        model.addConstrs(
            (U_jt[j, 1] == self.a_j[j] * W_jt[j, 1] -
             sum(x_jkt[j, k, 1] for k in self.K)
             for j in self.J),
            name="Condicion_borde_semillas"
        )

        model.addConstrs(
            (1 - x_jkt[j, k, t] >= sum(x_jkt[j, k, l] for l in range(t + 1, min(t + self.O_j[j] - 1, max(self.T)) + 1))
             for j in self.J for k in self.K for t in self.T if t < max(self.T)),
            name="Terminar_cosecha"
        )

        # Función objetivo
        model.setObjective(I_t[max(self.T)], GRB.MAXIMIZE)

        # Optimizamos el problema
        model.optimize()

        # Retornamos el modelo y las variables de decisión
        return (model, x_jkt)

    def manejo_soluciones(self, model, x_jkt) -> None:

        # Manejo de soluciones
        print("\n"+"-"*10+" Manejo Soluciones "+"-"*10)
        print()
        print(
            f"El valor óptimo de la función objetivo es: {model.objVal} unidades monetarias.")
        print()
        print("\n"+"-"*10+" Cantidad de veces que se planto en cada terreno "+"-"*10)
        print()
        veces_plantado = {k: 0 for k in self.K}
        for k in self.K:
            for t in self.T:
                for j in self.J:
                    if x_jkt[j, k, t].x == 1:
                        veces_plantado[k] += 1
        for k in self.K:
            print(f"El terreno {k} se plantó {veces_plantado[k]} veces.")

    def ver_calendario(self, x_jkt) -> None:
        '''
        Ver el calendario de siembra
        donde se muestra el cuadrante, la semilla
        que se siembra y 0 si no se siembra
        '''

        # Crear un DataFrame vacío con índices basados en self.K y columnas basadas en self.T
        df = pd.DataFrame(index=['Terreno ' + str(k) for k in self.K],
                          columns=['Mes ' + str(t) for t in self.T])

        # Rellenar el DataFrame con el tipo de semilla sembrada en cada cuadrante
        # o 0 si no se sembró nada
        for k in self.K:
            for t in self.T:
                semilla = 0
                for j in self.J:
                    if x_jkt[j, k, t].x == 1:
                        semilla = j
                df.at['Terreno ' + str(k), 'Mes ' + str(t)] = semilla

        # Convertir el DataFrame a csv
        df.to_csv('calendario.csv')


class MainWindow(QMainWindow):
    # Clase para mostrar el calendario en una ventana
    def __init__(self) -> None:
        super(MainWindow, self).__init__()
        self.setWindowTitle("Calendario de Siembra")

        # Leer el archivo CSV en un DataFrame
        df = pd.read_csv('calendario.csv', index_col=0)

        # Crear un QTableWidget y llenarlo con los datos del DataFrame
        self.table = QTableWidget()
        self.table.setRowCount(df.shape[0])
        self.table.setColumnCount(df.shape[1])
        self.table.setHorizontalHeaderLabels(df.columns)
        self.table.setVerticalHeaderLabels(df.index)

        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                self.table.setItem(i, j, QTableWidgetItem(str(df.iloc[i, j])))

        self.setCentralWidget(self.table)
        self.resize(1450, 300)
        self.move(200, 300)

        self.show()


if __name__ == '__main__':

    '''
    Instanciamos el modelo,
    mostramos soluciones
    y mostramos el calendario
    con una interfaz gráfica
    '''

    modelo = Modelo()
    variables = modelo.implementar_modelo()
    modelo.manejo_soluciones(*variables)
    print()
    print("-"*10+"Mostrando Calendario"+"-"*10)
    modelo.ver_calendario(variables[1])

    app = QApplication(sys.argv)
    mainWin = MainWindow()
    sys.exit(app.exec())
