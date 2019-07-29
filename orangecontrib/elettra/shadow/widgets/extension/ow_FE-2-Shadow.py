import os, sys
from PyQt5.QtWidgets import QApplication

import orangecanvas.resources as resources

#from oasys.widgets.error_profile.ow_abstract_height_profile_simulator import OWAbstractHeightErrorProfileSimulator
from orangecontrib.elettra.util.gui.ow_elettra_widget import ELETTRAWidget

from Shadow import ShadowTools as ST
from orangecontrib.shadow.util.shadow_objects import ShadowPreProcessorData

class OWthermal_load(ELETTRAWidget):
    name = "Thermal load data converter"
    description = "Converter from FE simulations to Shadow format"
    icon = "icons/simulator.png"
    author = "Aljosa Hafner"
    maintainer_email = "aljosa.hafner@ceric-eric.eu"
    priority = 10
    category = "User Defined"
    keywords = ["surface_data_converter"]

    outputs = [{"name": "PreProcessor_Data",
                "type": ShadowPreProcessorData,
                "doc": "PreProcessor Data",
                "id": "PreProcessor_Data"}]


    usage_path = os.path.join(resources.package_dirname("orangecontrib.elettra.shadow.widgets.extension"), "misc", "height_error_profile_usage.png")

    def __init__(self):
        super().__init__()

    def after_change_workspace_units(self):
        self.si_to_user_units = 1 / self.workspace_units_to_m

        self.axis.set_xlabel("X [" + self.workspace_units_label + "]")
        self.axis.set_ylabel("Y [" + self.workspace_units_label + "]")

        label = self.le_dimension_y.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_step_y.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_correlation_length_y.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

        label = self.le_dimension_x.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_step_x.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_correlation_length_x.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

        label = self.le_conversion_factor_y_x.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Abscissa)")
        label = self.le_conversion_factor_y_y.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Height Profile Values)")
        label = self.le_conversion_factor_x_x.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Abscissa)")
        label = self.le_conversion_factor_x_y.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Height Profile Values)")

        label = self.le_new_length_y_1.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_new_length_y_2.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_new_length_x_1.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_new_length_x_2.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")


    def get_usage_path(self):
        return self.usage_path

    def get_axis_um(self):
        return self.workspace_units_label

    def write_error_profile_file(self):
        ST.write_shadow_surface(self.zz, self.xx, self.yy, self.heigth_profile_file_name)

    def send_data(self, dimension_x, dimension_y):
        self.send("PreProcessor_Data", ShadowPreProcessorData(error_profile_data_file=self.heigth_profile_file_name,
                                                              error_profile_x_dim=dimension_x,
                                                              error_profile_y_dim=dimension_y))

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = OWthermal_load()
    ow.show()
    a.exec_()
    ow.saveSettings()
