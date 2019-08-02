import os, sys

from numpy import loadtxt, mgrid, array, savetxt, zeros, abs
from scipy.interpolate import griddata

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QLabel, QSizePolicy
from PyQt5.QtGui import QTextCursor, QFont, QPalette, QColor, QPixmap
from srxraylib.metrology import profiles_simulation

from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.pylab import colorbar

from orangewidget import gui, widget
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog
from oasys.util.oasys_util import EmittingStream

try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

class OWAbstractThermalLoadConverter(OWWidget):
    want_main_area = True
    want_control_area = True

    MAX_WIDTH = 1280
    MAX_HEIGHT = 720

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 512

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 512

    unit = Setting(0)
    method = Setting(0)
    spacing_value = Setting(0.0003)
    noPts_x = Setting(300)
    noPts_y = Setting(30)

    interp_grid_x = None
    interp_grid_y = None
    interp_grid_z = None

    simFE_fname = Setting("FEM_matrix.dat")
    save_height_profile_file_name = Setting('FEtoShadow.dat')

    inputs=[("FE 2D array", array, "selectFile")]

    def __init__(self):
        super().__init__()

        #/ Make GUI ----------------------------------------------------------------------------------------------------
        self.runaction = widget.OWAction("Import Simulated Array", self)
        self.runaction.triggered.connect(self.selectFile)
        self.addAction(self.runaction)

        self.runaction = widget.OWAction("Generate Height Profile File", self)
        self.runaction.triggered.connect(self.interp_save)
        self.addAction(self.runaction)

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width() * 0.05),
                               round(geom.height() * 0.05),
                               round(min(geom.width() * 0.98, self.MAX_WIDTH)),
                               round(min(geom.height() * 0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Import Simulated\nArray", callback=self.selectFile)
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Generate Height\nProfile File", callback=self.interp_save)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette())  # make a copy of the palette
        button.setFixedHeight(45)
        button.setFixedWidth(150)

        button = gui.button(button_box, self, "Reset Fields", callback=self.call_reset_settings)
        button.setFixedHeight(45)

        #/ Control area ------------------------------------------------------------------------------------------------

        gui.separator(self.controlArea)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_input = oasysgui.createTabPage(tabs_setting, "Input Parameters")
        tab_out = oasysgui.createTabPage(tabs_setting, "Output")
        tab_usa = oasysgui.createTabPage(tabs_setting, "Use of the Widget")
        tab_usa.setStyleSheet("background-color: white;")

        usage_box = oasysgui.widgetBox(tab_usa, "", addSpace=True, orientation="horizontal")

        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setPixmap(QPixmap(self.get_usage_path()))

        usage_box.layout().addWidget(label)

        #/ ---------------------------------------

        select_file_box_1 = oasysgui.widgetBox(tab_input, "", addSpace=True, orientation="horizontal")
        self.wi_simFE_fname = oasysgui.lineEdit(select_file_box_1, self, "simFE_fname", "Input Array Path",
                                                labelWidth=120, valueType=str, orientation="horizontal")

        input_box = oasysgui.widgetBox(tab_input, "Transformation settings", addSpace=True, orientation="vertical")

        gui.comboBox(input_box, self, "unit", label="Unit", labelWidth=260,
                     items=["m", "cm"],
                     callback=None, sendSelectedValue=False, orientation="horizontal")

        gui.separator(input_box)
        gui.separator(input_box)

        gui.comboBox(input_box, self, "method", label="Select method", labelWidth=260,
                     items=["Spacing", "Number of points"],
                     callback=self.set_Method, sendSelectedValue=False, orientation="horizontal")

        self.method_box_1 = oasysgui.widgetBox(input_box, "", addSpace=True, orientation="vertical", height=70)

        self.method_box_1_1 = oasysgui.widgetBox(self.method_box_1, "", addSpace=True, orientation="vertical")
        self.wi_spacing_value = oasysgui.lineEdit(self.method_box_1_1, self, "spacing_value", "Spacing size",
                                                  labelWidth=260, valueType=float, orientation="horizontal")

        self.method_box_1_2 = oasysgui.widgetBox(self.method_box_1, "", addSpace=True, orientation="vertical")
        self.wi_noPts_x = oasysgui.lineEdit(self.method_box_1_2, self, "noPts_x", "X",
                                         labelWidth=260, valueType=int, orientation="horizontal")
        self.wi_noPts_y = oasysgui.lineEdit(self.method_box_1_2, self, "noPts_y", "Y",
                                         labelWidth=260, valueType=int, orientation="horizontal")

        self.set_Method()

        output_box = oasysgui.widgetBox(tab_input, "Output settings", addSpace=True, orientation="vertical")
        select_file_box_2 = oasysgui.widgetBox(output_box, "", addSpace=True, orientation="horizontal")
        self.wi_save_height_profile_file_name = oasysgui.lineEdit(select_file_box_2, self,
                                                                  "save_height_profile_file_name", "Output Array Path",
                                                                  labelWidth=120, valueType=str, orientation="horizontal")
        gui.button(select_file_box_2, self, "Browse", callback=self.selectFile_save)

        gui.rubber(self.controlArea)

        self.shadow_output = oasysgui.textArea()

        out_box = oasysgui.widgetBox(tab_out, "System Output", addSpace=True, orientation="horizontal", height=580)
        out_box.layout().addWidget(self.shadow_output)

        gui.rubber(self.controlArea)

        self.figure = Figure(figsize=(600, 600))
        self.figure.patch.set_facecolor('white')

        self.axis = self.figure.add_subplot(111)

        self.figure_canvas = FigureCanvasQTAgg(self.figure)
        self.mainArea.layout().addWidget(self.figure_canvas)

        gui.rubber(self.mainArea)

    def get_usage_path(self):
        pass

    def set_Method(self):
        self.method_box_1.setVisible(self.method<2)
        self.method_box_1_1.setVisible(self.method==0)
        self.method_box_1_2.setVisible(self.method==1)


    def calculate_height_profile_ni(self):
        self.calculate_height_profile(not_interactive_mode=True)

    def generate_FEtoShadow(self, not_interactive_mode=False):
        try:
            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            node, number, x, y, z = loadtxt(self.simFE_fname, skiprows=1, unpack=True)

            if self.method == 0: # Spacing
                noPts = (abs(min(x)) + abs(max(x))) / self.spacing_value
                step = self.spacing_value
                if noPts > 500:
                    QMessageBox.critical(self, "Error",
                                         "Select larger spacing. Current number of points: {}\nNumber of points cannot be larger than 500!".format(int(noPts)), QMessageBox.Ok)
                else:
                    grid = mgrid[min(x):max(x)+step:step, min(y):max(y)+step:step]

            elif self.method == 1: # Number of points
                if self.noPts_x > 500:
                    QMessageBox.critical(self, "Error",
                                         "Select fewer points in x.\nNumber of points cannot be larger than 500!", QMessageBox.Ok)
                else:
                    grid = mgrid[min(x):max(x):(1j*self.noPts_x), min(y):max(y):(1j*self.noPts_y)]
            else:
                QMessageBox.critical(self, "Error", "Error in: method. Can be only 0 or 1", QMessageBox.Ok)

            grid_z = griddata((x, y), z, (grid[0], grid[1]), method='cubic')

            # self.interp_save()

            self.axis.clear()

            if self.unit == 0: # metres [m]
                uname = 'm'
                unit = 1.
            elif self.unit == 1: # centimetres [cm]
                uname = 'cm'
                unit = 1e2

            im = self.axis.contourf(grid[0] * unit, grid[1] * unit, grid_z * 1e9, cmap='jet')

            self.axis.set_xlabel("X [{}]".format(uname))
            self.axis.set_ylabel("Y [{}]".format(uname))
            self.axis.set_xlim(min(x) * unit, max(x) * unit)
            self.axis.set_ylim(min(y) * unit, max(y) * unit)
            self.axis.set_title('Interpolated surface')
            cb = self.figure.colorbar(im)
            cb.ax.set_ylabel('Z [nm]')

            self.interp_grid_x = grid[0]
            self.interp_grid_y = grid[1]
            self.interp_grid_z = grid_z

            self.figure_canvas.draw()

            # if not not_interactive_mode:
            #     self.figure_canvas.draw()
            #
            #     QMessageBox.information(self, "QMessageBox.information()",
            #                             "Height Profile calculated: if the result is satisfactory,\nclick \'Generate Height Profile File\' to complete the operation ",
            #                             QMessageBox.Ok)
        except Exception as exception:
            QMessageBox.critical(self, "Error", exception.args[0], QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def interp_save(self, not_interactive_mode=False):
        try:
            congruence.checkDir(self.save_height_profile_file_name)

            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            congruence.checkFileName(self.save_height_profile_file_name)

            self.write_error_profile_file()

            if not not_interactive_mode:
                QMessageBox.information(self, "QMessageBox.information()",
                                        "Height Profile file " + self.save_height_profile_file_name + " written on disk",
                                        QMessageBox.Ok)

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def write_error_profile_file(self):

        if self.unit == 0:  # metres [m]
            uname = 'm'
            unit = 1.
        elif self.unit == 1:  # centimetres [cm]
            uname = 'cm'
            unit = 1e2

        grid_z = self.interp_grid_z.T
        self.interp_grid_x = self.interp_grid_x * unit
        self.interp_grid_y = self.interp_grid_y * unit
        final_array = zeros((grid_z.shape[0], grid_z.shape[1] + 1))
        final_array[:,0] = self.interp_grid_y[0,:]
        final_array[:,1:] = grid_z

        head_1 = '{} {}\n'.format(grid_z.shape[0], grid_z.shape[1])
        head_2 = ' '.join(str(n) for n in self.interp_grid_x[:, 0])
        head = head_1 + head_2

        # Can be improved by using Shadow.ShadowTools.write_shadow_surface()
        savetxt(self.save_height_profile_file_name, final_array, header=head, comments='', fmt='%.11e')


    def send_data(self, dimension_x, dimension_y):
        raise NotImplementedError("This method is abstract")

    def call_reset_settings(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Reset of the Fields?"):
            try:
                self.resetSettings()
            except:
                pass

    # def check_fields(self):
    #     if self.kind_of_profile_y < 2:
    #         self.dimension_y = congruence.checkStrictlyPositiveNumber(self.dimension_y, "Dimension Y")
    #         self.step_y = congruence.checkStrictlyPositiveNumber(self.step_y, "Step Y")
    #         if self.kind_of_profile_y == 0: self.power_law_exponent_beta_y = congruence.checkPositiveNumber(self.power_law_exponent_beta_y, "Beta Value Y")
    #         if self.kind_of_profile_y == 1: self.correlation_length_y = congruence.checkStrictlyPositiveNumber(self.correlation_length_y, "Correlation Length Y")
    #         self.rms_y = congruence.checkPositiveNumber(self.rms_y, "Rms Y")
    #         self.montecarlo_seed_y = congruence.checkPositiveNumber(self.montecarlo_seed_y, "Monte Carlo initial seed y")
    #     else:
    #         congruence.checkFile(self.heigth_profile_1D_file_name_y)
    #         self.conversion_factor_y_x = congruence.checkStrictlyPositiveNumber(self.conversion_factor_y_x, "Conversion from file to meters (Abscissa)")
    #         self.conversion_factor_y_y = congruence.checkStrictlyPositiveNumber(self.conversion_factor_y_y, "Conversion from file to meters (Height Profile Values)")
    #         if self.modify_y > 0:
    #             self.new_length_y = congruence.checkStrictlyPositiveNumber(self.new_length_y, "New Length")
    #         if self.renormalize_y == 1:
    #             self.rms_y = congruence.checkPositiveNumber(self.rms_y, "Rms Y")
    #
    #     if self.kind_of_profile_x < 2:
    #         self.dimension_x = congruence.checkStrictlyPositiveNumber(self.dimension_x, "Dimension X")
    #         self.step_x = congruence.checkStrictlyPositiveNumber(self.step_x, "Step X")
    #         if self.kind_of_profile_x == 0: self.power_law_exponent_beta_x = congruence.checkPositiveNumber(self.power_law_exponent_beta_x, "Beta Value X")
    #         if self.kind_of_profile_x == 1: self.correlation_length_x = congruence.checkStrictlyPositiveNumber(self.correlation_length_x, "Correlation Length X")
    #         self.rms_x = congruence.checkPositiveNumber(self.rms_x, "Rms X")
    #         self.montecarlo_seed_x = congruence.checkPositiveNumber(self.montecarlo_seed_x, "Monte Carlo initial seed X")
    #     else:
    #         congruence.checkFile(self.heigth_profile_1D_file_name_x)
    #         self.conversion_factor_x_x = congruence.checkStrictlyPositiveNumber(self.conversion_factor_x_x, "Conversion from file to meters (Abscissa)")
    #         self.conversion_factor_x_y = congruence.checkStrictlyPositiveNumber(self.conversion_factor_x_y, "Conversion from file to meters (Height Profile Values)")
    #         if self.modify_x > 0:
    #             self.new_length_x = congruence.checkStrictlyPositiveNumber(self.new_length_x, "New Length")
    #         if self.renormalize_x == 1:
    #             self.rms_x = congruence.checkPositiveNumber(self.rms_x, "Rms X")
    #
    #     congruence.checkDir(self.heigth_profile_file_name)

    def writeStdOut(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

    def selectFile(self):
        self.wi_simFE_fname.setText(oasysgui.selectFileFromDialog(self, self.simFE_fname, "Select Input Folder", file_extension_filter="Data Files (*.dat *.txt)"))
        self.generate_FEtoShadow(self)

    def selectFile_save(self):
        self.wi_save_height_profile_file_name.setText(oasysgui.selectDirectoryFromDialog(self, "Select Output Folder", self.save_height_profile_file_name))
        self.save_height_profile_file_name = self.save_height_profile_file_name + '/FEtoShadow.dat'

    def get_axis_um(self):
        return "m"