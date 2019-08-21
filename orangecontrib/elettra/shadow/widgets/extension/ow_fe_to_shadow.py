from PyQt5.QtWidgets import QApplication

import os, sys

import orangecanvas.resources as resources

from orangecontrib.elettra.util.gui.ow_abstract_thermal_load_converter import OWAbstractThermalLoadConverter

class OWthermal_load(OWAbstractThermalLoadConverter):
    name = "Thermal load data converter"
    id = "thermal_load_data_converter"
    description = "Converter from FE simulations to Shadow format"
    icon = "icons/thermal_load.png"
    author = "Aljosa Hafner"
    author_email = "aljosa.hafner(@at@)ceric-eric.eu"
    priority = 2
    category = ""
    keywords = ["thermal", "load", "converter"]

    # outputs = [{"name": "PreProcessor_Data",
    #             "type": ShadowPreProcessorData,
    #             "doc": "PreProcessor Data",
    #             "id": "PreProcessor_Data"}]

    #TODO: Here comes the usage diagram, not so urgent, using the one from flux calculator at the moment...
    usage_path = os.path.join(resources.package_dirname("orangecontrib.elettra.shadow.widgets.extension"), "misc", "thermal_load_usage.png")

    def __init__(self):
        super().__init__()

    def get_usage_path(self):
        return self.usage_path

    def get_axis_um(self):
        return self.workspace_units_label

    # def send_data(self, dimension_x, dimension_y):
    #     self.send("PreProcessor_Data", ShadowPreProcessorData(error_profile_data_file=self.heigth_profile_file_name,
    #                                                           error_profile_x_dim=dimension_x,
    #                                                           error_profile_y_dim=dimension_y))
    # def write_error_profile_file(self):
    #     ST.write_shadow_surface(self.zz, self.xx, self.yy, self.heigth_profile_file_name)