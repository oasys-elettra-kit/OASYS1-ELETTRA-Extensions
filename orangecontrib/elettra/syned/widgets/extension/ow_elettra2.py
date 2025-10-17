import os, sys
import numpy
import pandas
import scipy.constants as codata


from syned.storage_ring.magnetic_structures.undulator import Undulator
from syned.storage_ring.magnetic_structures.wiggler import Wiggler

from syned.storage_ring.magnetic_structures import insertion_device

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import QRect

from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog

from syned.storage_ring.light_source import LightSource, ElectronBeam
from syned.beamline.beamline import Beamline

from oasys.widgets.gui import ConfirmDialog

import orangecanvas.resources as resources

from syned.util.json_tools import load_from_json_file


m2ev = codata.c * codata.h / codata.e

VERTICAL = 1
HORIZONTAL = 2
BOTH = 3

#TODO: Implement the parametrization of B

class OWELETTRA2(OWWidget):

    name = "Elettra 2.0 Sources"
    description = "Syned: Elettra 2.0 ID Light Source"
    icon = "icons/elettra_source.png"
    priority = 2.0


    maintainer = "Juan Reyes Herrera"
    maintainer_email = "juan.reyesherrera(@at@)elettra.eu"
    category = "Elettra2 Syned Light Sources"
    keywords = ["data", "file", "load", "read"]

    outputs = [{"name":"SynedData",
                "type":Beamline,
                "doc":"Syned Beamline",
                "id":"data"}]


    want_main_area = 1


    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 650

    TABS_AREA_HEIGHT = 625
    CONTROL_AREA_WIDTH = 450


    electron_energy_in_GeV = Setting(2.4)
    electron_energy_spread = Setting(0.000934)
    ring_current           = Setting(0.4)
    number_of_bunches      = Setting(0.0)

    use_dispersion = Setting(1) # 0 no, 1 yes

    moment_xx           = Setting(0.0)
    moment_xxp          = Setting(0.0)
    moment_xpxp         = Setting(0.0)
    moment_yy           = Setting(0.0)
    moment_yyp          = Setting(0.0)
    moment_ypyp         = Setting(0.0)

    electron_beam_size_h       = Setting(0.0)
    electron_beam_divergence_h = Setting(0.0)
    electron_beam_size_v       = Setting(0.0)
    electron_beam_divergence_v = Setting(0.0)

    electron_beam_emittance_h = Setting(0.0)
    electron_beam_emittance_v = Setting(0.0)
    electron_beam_beta_h = Setting(0.0)
    electron_beam_beta_v = Setting(0.0)
    electron_beam_alpha_h = Setting(0.0)
    electron_beam_alpha_v = Setting(0.0)
    electron_beam_eta_h = Setting(0.0)
    electron_beam_eta_v = Setting(0.0)
    electron_beam_etap_h = Setting(0.0)
    electron_beam_etap_v = Setting(0.0)

    type_of_properties = Setting(1)
    type_of_properties_initial_selection = type_of_properties

    auto_energy = Setting(0.0)
    auto_harmonic_number = Setting(1)

    K_horizontal       = Setting(0.5)
    K_vertical         = Setting(0.5)
    period_length      = Setting(0.018)
    number_of_periods  = Setting(10)

    elettra_bl_index = Setting(0)
    elettra_id_index= Setting(0)
    gap_mm = Setting(0.0)

    gap_min = Setting(5.0)
    gap_max = Setting(30.0)
    harmonic_max = Setting(3)

    a0 = Setting('3.694')
    a1 = Setting('-5.068')
    a2 = Setting('')
    a3 = Setting('')
    a4 = Setting('')
    a5 = Setting('')
    a6 = Setting('')

    #pow_dens_screen = Setting(30.0)
    
    data_url = os.path.join(resources.package_dirname("orangecontrib.elettra.syned.data"), 'elettra2_sources.csv')
    data_ls = os.path.join(resources.package_dirname("orangecontrib.elettra.syned.data"), 'Elettra_Long_Straight.json')
    data_ss = os.path.join(resources.package_dirname("orangecontrib.elettra.syned.data"), 'Elettra_Short_Straight.json')

    data_dict = None

    def __init__(self):

        self.get_data_dictionary_csv() #reads the CSV file with the sources info
        self.get_ls_electronbeam() #reads long section e-beam parameters JSON
        self.get_ss_electronbeam() #reads short section e-beam parameters JSON        

        self.runaction = widget.OWAction("Send Data", self)
        self.runaction.triggered.connect(self.send_data)
        self.addAction(self.runaction)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Send Data", callback=self.send_data)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Reset Fields", callback=self.callResetSettings)
        font = QFont(button.font())
        font.setItalic(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Red'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)
        button.setFixedWidth(150)

        gui.separator(self.controlArea)

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width()*0.05),
                               round(geom.height()*0.05),
                               round(min(geom.width()*0.98, self.MAX_WIDTH)),
                               round(min(geom.height()*0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        self.tabs_setting = oasysgui.tabWidget(self.controlArea)
        self.tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        self.tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        self.tab_sou = oasysgui.createTabPage(self.tabs_setting, "Light Source Setting")

        gui.comboBox(self.tab_sou, self, "elettra_bl_index", label="Load ID parameters from Beamline name: ", labelWidth=350,
                     items=self.get_bl_list(), callback=self.set_bl, sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(self.tab_sou, self, "elettra_id_index", label="Load ID parameters from ID name: ", labelWidth=350,
                     items=self.get_id_list(), callback=self.set_id, sendSelectedValue=False, orientation="horizontal")

        self.electron_beam_box = oasysgui.widgetBox(self.tab_sou, "Electron Beam/Machine Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.electron_beam_box, self, "electron_energy_in_GeV", "Energy [GeV]",  labelWidth=260, valueType=float, orientation="horizontal", callback=self.update)
        oasysgui.lineEdit(self.electron_beam_box, self, "electron_energy_spread", "Energy Spread", labelWidth=260, valueType=float, orientation="horizontal", callback=self.update)
        oasysgui.lineEdit(self.electron_beam_box, self, "ring_current", "Ring Current [A]",        labelWidth=260, valueType=float, orientation="horizontal", callback=self.update)

        gui.comboBox(self.electron_beam_box, self, "type_of_properties", label="Electron Beam Properties", labelWidth=350,
                     items=["From 2nd Moments", "From Size/Divergence", "From Twiss papameters","Zero emittance", "Elettra2-LS", "Elettra2-SS"],
                     callback=self.update_electron_beam,
                     sendSelectedValue=False, orientation="horizontal")
        #box = gui.widgetBox(self.controlArea, "Options")
        gui.comboBox(self.electron_beam_box, self, "use_dispersion", label="Use Dispersion in Size/Divergence and Moments calculations", labelWidth=350,
                     items=["No","Yes"],
                     callback=self.set_use_dispersion,
                     sendSelectedValue=False, orientation="horizontal")
        

        self.left_box_2_1 = oasysgui.widgetBox(self.electron_beam_box, "", addSpace=False, orientation="horizontal", height=150)
        
        self.left_box_2_1_l = oasysgui.widgetBox(self.left_box_2_1, "", addSpace=False, orientation="vertical")
        self.left_box_2_1_r = oasysgui.widgetBox(self.left_box_2_1, "", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(self.left_box_2_1_l, self, "moment_xx",   "<xx>[m^2]",    labelWidth=70, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_1_l, self, "moment_xxp",  "<xx'>[m.rad]", labelWidth=70, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_1_l, self, "moment_xpxp", "<x'x'>[rad^2]",labelWidth=70, valueType=float, orientation="horizontal",  callback=self.update)

        oasysgui.lineEdit(self.left_box_2_1_r, self, "moment_yy",   "<yy>[m^2]",    labelWidth=70, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_1_r, self, "moment_yyp",  "<yy'>[m.rad]", labelWidth=70, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_1_r, self, "moment_ypyp", "<y'y'>[rad^2]",labelWidth=70, valueType=float, orientation="horizontal",  callback=self.update)


        self.left_box_2_2 = oasysgui.widgetBox(self.electron_beam_box, "", addSpace=False, orientation="vertical", height=150)

        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_size_h",       "Horizontal Beam Size \u03c3x [m]",          labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_size_v",       "Vertical Beam Size \u03c3y [m]",            labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_divergence_h", "Horizontal Beam Divergence \u03c3'x [rad]", labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_2, self, "electron_beam_divergence_v", "Vertical Beam Divergence \u03c3'y [rad]",   labelWidth=260, valueType=float, orientation="horizontal",  callback=self.update)

        self.left_box_2_3 = oasysgui.widgetBox(self.electron_beam_box, "", addSpace=False, orientation="horizontal",height=150)
        self.left_box_2_3_l = oasysgui.widgetBox(self.left_box_2_3, "", addSpace=False, orientation="vertical")
        self.left_box_2_3_r = oasysgui.widgetBox(self.left_box_2_3, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_emittance_h", "\u03B5x [m.rad]",labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_alpha_h",     "\u03B1x",        labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_beta_h",      "\u03B2x [m]",    labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_eta_h",       "\u03B7x",        labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_l, self, "electron_beam_etap_h",      "\u03B7'x",       labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)


        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_emittance_v", "\u03B5y [m.rad]",labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_alpha_v",     "\u03B1y",        labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_beta_v",      "\u03B2y [m]",    labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_eta_v",       "\u03B7y",        labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)
        oasysgui.lineEdit(self.left_box_2_3_r, self, "electron_beam_etap_v",      "\u03B7'y",       labelWidth=75, valueType=float, orientation="horizontal",  callback=self.update)

        gui.rubber(self.controlArea)

        ###################

        left_box_1 = oasysgui.widgetBox(self.tab_sou, "ID Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "period_length", "Period Length [m]", labelWidth=260,
                          valueType=float, orientation="horizontal", callback=self.update)
        oasysgui.lineEdit(left_box_1, self, "number_of_periods", "Number of Periods", labelWidth=260,
                          valueType=float, orientation="horizontal", callback=self.update)



        left_box_1 = oasysgui.widgetBox(self.tab_sou, "Setting", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "K_horizontal", "Horizontal K", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "K_vertical", "Vertical K", labelWidth=260,
                          valueType=float, orientation="horizontal", callback=self.set_K)

        oasysgui.lineEdit(left_box_1, self, "gap_mm", "Undulator Gap [mm]",
                          labelWidth=250, valueType=float, orientation="horizontal",
                          callback=self.update)

        left_box_2 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical")
        oasysgui.lineEdit(left_box_2, self, "auto_energy", "Photon Energy [eV]",
                          labelWidth=250, valueType=float, orientation="horizontal",
                          callback=self.auto_set_undulator_V)
        oasysgui.lineEdit(left_box_2, self, "auto_harmonic_number", "Harmonic",
                          labelWidth=250, valueType=int, orientation="horizontal",
                          callback=self.auto_set_undulator_V)

        self.initializeTabs()
        self.populate_electron_beam()
        self.set_visible()
        self.update()

    def get_bl_list(self):
        out_list = [self.data_dict["beamline_name"][i] for i in
                   range(len(self.data_dict["beamline_name"]))]

        out_list.insert(0,"<None>") # We add None at the beginning: elettra_bl_name is the dict index plus one
        return out_list


    def get_id_list(self):
        out_list = [self.data_dict["id_name"][i] for i in
                   range(len(self.data_dict["id_name"]))]

        out_list.insert(0,"<None>") # We add None at the beginning: elettra_id_name is the dict index plus one
        return out_list


    def initializeTabs(self):
        self.tabs = oasysgui.tabWidget(self.mainArea)

        self.tab = [oasysgui.createTabPage(self.tabs, "Info",),
                    ]

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)


        self.info_id = oasysgui.textArea(height=self.IMAGE_HEIGHT-5, width=self.IMAGE_WIDTH-5)
        profile_box = oasysgui.widgetBox(self.tab[0], "", addSpace=True, orientation="horizontal",
                                         height = self.IMAGE_HEIGHT, width=self.IMAGE_WIDTH-5)
        profile_box.layout().addWidget(self.info_id)                   
        
        self.tabs.setCurrentIndex(1)

    def check_magnetic_structure(self):
        congruence.checkPositiveNumber(self.K_horizontal, "Horizontal K")
        congruence.checkPositiveNumber(self.K_vertical, "Vertical K")
        congruence.checkStrictlyPositiveNumber(self.period_length, "Period Length")
        congruence.checkStrictlyPositiveNumber(self.number_of_periods, "Number of Periods")

    def set_use_dispersion(self):
        if self.use_dispersion == 0:
            self.use_dispersion = False
        else:
            self.use_dispersion = True
        self.update()
        self.set_id()

    def set_ls_electron_beam(self):
        # print("Setting LS e-beam")
        # First we set the type of properties to 2, so that the values
        # are taken from the JSON     

        self.type_of_properties = 2        
        ex, ax, bx, ey, ay, by = self.ls_electronbeam.get_twiss_all()
        nx, npx, ny, npy = self.ls_electronbeam.get_dispersion_all()
        
        self.electron_beam_beta_h = bx
        self.electron_beam_beta_v = by
        self.electron_beam_alpha_h = ax
        self.electron_beam_alpha_v = ay
        self.electron_beam_eta_h = nx
        self.electron_beam_eta_v = ny
        self.electron_beam_etap_h = npx
        self.electron_beam_etap_v = npy
        self.electron_beam_emittance_h = ex
        self.electron_beam_emittance_v = ey

        # Now we calculate the size and divergence from the Twiss parameters
        # including dispersion

        eb = self.get_electron_beam()

        x, xp, y, yp = eb.get_sigmas_all(dispersion=self.use_dispersion)
        self.electron_beam_size_h =       numpy.round(x,12) 
        self.electron_beam_size_v =       numpy.round(y,12)
        self.electron_beam_divergence_h = numpy.round(xp,12)
        self.electron_beam_divergence_v = numpy.round(yp,12) 

        # Here we calculate the 2nd moments from the Twiss parameters
        # including dispersion       

        moment_xx, moment_xxp, moment_xpxp, moment_yy, moment_yyp, moment_ypyp = eb.get_moments_all(dispersion=self.use_dispersion)
        self.moment_xx   = moment_xx
        self.moment_yy   = moment_yy
        self.moment_xxp  = moment_xxp
        self.moment_yyp  = moment_yyp
        self.moment_xpxp = moment_xpxp
        self.moment_ypyp = moment_ypyp       

        # in order to keep the tag of properties selection

        if self.type_of_properties_initial_selection < 4:
            self.type_of_properties = self.type_of_properties_initial_selection
    
    def set_ss_electron_beam(self):
        #print("Setting SS e-beam")        
        self.type_of_properties = 2       
        ex, ax, bx, ey, ay, by = self.ss_electronbeam.get_twiss_all()
        nx, npx, ny, npy = self.ss_electronbeam.get_dispersion_all()
        
        self.electron_beam_beta_h = bx
        self.electron_beam_beta_v = by
        self.electron_beam_alpha_h = ax
        self.electron_beam_alpha_v = ay
        self.electron_beam_eta_h = nx
        self.electron_beam_eta_v = ny
        self.electron_beam_etap_h = npx
        self.electron_beam_etap_v = npy
        self.electron_beam_emittance_h = ex
        self.electron_beam_emittance_v = ey

        eb = self.get_electron_beam()

        x, xp, y, yp = eb.get_sigmas_all(dispersion=self.use_dispersion)
        self.electron_beam_size_h =       numpy.round(x,12) 
        self.electron_beam_size_v =       numpy.round(y,12)
        self.electron_beam_divergence_h = numpy.round(xp,12)
        self.electron_beam_divergence_v = numpy.round(yp,12)
        #        

        moment_xx, moment_xxp, moment_xpxp, moment_yy, moment_yyp, moment_ypyp = eb.get_moments_all(dispersion=self.use_dispersion)
        self.moment_xx   = moment_xx
        self.moment_yy   = moment_yy
        self.moment_xxp  = moment_xxp
        self.moment_yyp  = moment_yyp
        self.moment_xpxp = moment_xpxp
        self.moment_ypyp = moment_ypyp

        # in order to keep the tag of properties selection

        if self.type_of_properties_initial_selection < 4:
            self.type_of_properties = self.type_of_properties_initial_selection
    
    def get_bl_number(self):
        if self.elettra_id_index == 0: # <None>
            bl = 1 # this is by convention, zero would give errors
        else:
            label = self.get_bl_list()[self.elettra_bl_index]
            bl= int(label[2:4])
        return bl

    def get_id_number(self):
        if self.elettra_id_index == 0: # <None>
            id = 1 # this is by convention, zero would give errors
        else:
            label = self.get_id_list()[self.elettra_id_index]
            id = int(label[2:4])
        return id


    def update_electron_beam(self):
        self.type_of_properties_initial_selection = self.type_of_properties

        if self.type_of_properties_initial_selection == 4:
            self.set_ls_electron_beam()
        elif self.type_of_properties_initial_selection == 5:
            self.set_ss_electron_beam()
        self.set_visible()
        self.update()    

    def update(self):
        self.check_data()
        self.update_info()        

    def update_info(self):

        syned_electron_beam = self.get_electron_beam()
        syned_undulator = self.get_magnetic_structure()

        gamma = self.gamma()

        if self.elettra_id_index == 0:
            id = "<None>"
            elettra_beamline = "<None>"
            position = "<None>"
            id_naming = "<None>"
            
        else:
            id = self.data_dict["id_name"][self.elettra_id_index-1]
            elettra_beamline = self.data_dict["beamline_name"][self.elettra_id_index-1]
            position = self.data_dict["position"][self.elettra_id_index-1]
            id_naming = self.data_dict["naming"][self.elettra_id_index-1]

        info_parameters = {
            "electron_energy_in_GeV":self.electron_energy_in_GeV,
            "gamma":"%8.3f"%self.gamma(),
            "ring_current":"%4.3f "%syned_electron_beam.current(),
            "K_horizontal":syned_undulator.K_horizontal(),
            "K_vertical": syned_undulator.K_vertical(),
            "period_length": syned_undulator.period_length(),
            "number_of_periods": syned_undulator.number_of_periods(),
            "undulator_length": syned_undulator.length(),
            "resonance_energy":"%6.3f"%syned_undulator.resonance_energy(gamma,harmonic=1),
            "resonance_energy3": "%6.3f" % syned_undulator.resonance_energy(gamma,harmonic=3),
            "resonance_energy5": "%6.3f" % syned_undulator.resonance_energy(gamma,harmonic=5),
            "B_horizontal":"%4.2F"%syned_undulator.magnetic_field_horizontal(),
            "B_vertical": "%4.2F" % syned_undulator.magnetic_field_vertical(),
            "cc_1": "%4.2f" % (1e6*syned_undulator.gaussian_central_cone_aperture(gamma,1)),
            "cc_3": "%4.2f" % (1e6*syned_undulator.gaussian_central_cone_aperture(gamma,3)),
            "cc_5": "%4.2f" % (1e6*syned_undulator.gaussian_central_cone_aperture(gamma,5)),
            # "cc_7": "%4.2f" % (self.gaussian_central_cone_aperture(7)*1e6),
            "sigma_rad": "%5.2f"        % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=1)[0]),
            "sigma_rad_prime": "%5.2f"  % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=1)[1]),
            "sigma_rad3": "%5.2f"       % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=3)[0]),
            "sigma_rad_prime3": "%5.2f" % (1e6*syned_undulator.get_sigmas_radiation(gamma,harmonic=3)[1]),
            "sigma_rad5": "%5.2f" % (1e6 * syned_undulator.get_sigmas_radiation(gamma, harmonic=5)[0]),
            "sigma_rad_prime5": "%5.2f" % (1e6 * syned_undulator.get_sigmas_radiation(gamma, harmonic=5)[1]),
            "first_ring_1": "%5.2f" % (1e6*syned_undulator.get_resonance_ring(gamma, harmonic=1, ring_order=1)),
            "first_ring_3": "%5.2f" % (1e6*syned_undulator.get_resonance_ring(gamma, harmonic=3, ring_order=1)),
            "first_ring_5": "%5.2f" % (1e6*syned_undulator.get_resonance_ring(gamma, harmonic=5, ring_order=1)),
            "Sx": "%5.2f"  % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[0]),
            "Sy": "%5.2f"  % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[1]),
            "Sxp": "%5.2f" % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[2]),
            "Syp": "%5.2f" % (1e6*syned_undulator.get_photon_sizes_and_divergences(syned_electron_beam)[3]),
            "und_power": "%5.2f" % syned_undulator.undulator_full_emitted_power(gamma,syned_electron_beam.current()),
            "CF_h": "%4.3f" % syned_undulator.approximated_coherent_fraction_horizontal(syned_electron_beam,harmonic=1),
            "CF_v": "%4.3f" % syned_undulator.approximated_coherent_fraction_vertical(syned_electron_beam,harmonic=1),
            "CF": "%4.3f" % syned_undulator.approximated_coherent_fraction(syned_electron_beam,harmonic=1),
            "url": self.data_url,
            "id": id,
            "beamline":elettra_beamline,
            "position":position,
            "id_naming":id_naming,
            "gap_min": "%4.3f" % self.gap_min,
            "gap_mm": "%4.3f" % self.gap_mm,
            "a0": "%s" % str(self.a0),
            "a1": "%s" % str(self.a1),
            "a2": "%s" % str(self.a2),
            "a3": "%s" % str(self.a3),
            "a4": "%s" % str(self.a4),
            "a5": "%s" % str(self.a5),
            "a6": "%s" % str(self.a6),
            }

        self.info_id.setText(self.info_template().format_map(info_parameters))        


    def info_template(self):
        return \
"""
data url: {url}
id_name: {id}
beamline: {beamline}
position: {position}
id_naming: {id_naming}

================ input parameters ===========
Electron beam energy [GeV]: {electron_energy_in_GeV}
Electron current:           {ring_current}
Period Length [m]:          {period_length}
Number of Periods:          {number_of_periods}

Horizontal K:               {K_horizontal}
Vertical K:                 {K_vertical}
Minimum gap (if nan: FIXED):{gap_min}
==============================================

Electron beam gamma:                {gamma}
Undulator Length [m]:               {undulator_length}
Horizontal Peak Magnetic field [T]: {B_horizontal}
Vertical Peak Magnetic field [T]:   {B_vertical}

Total power radiated by the undulator [W]: {und_power}

#TODO: Not yet implemented#
Gap in use: {gap_mm} mm
Using gap parametrization: 
    a0: {a0}
    a1: {a1}
    a2: {a2}
    a3: {a3}
    a4: {a4}
    a5: {a5}
    a6: {a6}

Note on calculation: #TODO Not yet implemented# 
A = [a0,a1,a2,...]
For IVU:
Bmax = a0 * exp(a1 * (gap[mm] / id_period[mm]) + a0 * exp(a2 * ((gap[mm] / id_period[mm])**2)

Resonances:

Photon energy [eV]: 
       for harmonic 1 : {resonance_energy}
       for harmonic 3 : {resonance_energy3}
       for harmonic 5 : {resonance_energy5}

Central cone (RMS urad):
       for harmonic 1 : {cc_1}
       for harmonic 3 : {cc_3}
       for harmonic 5 : {cc_5}

First ring at (urad):
       for harmonic 1 : {first_ring_1}
       for harmonic 3 : {first_ring_3}
       for harmonic 5 : {first_ring_5}

Sizes and divergences of radiation :
    at 1st harmonic: sigma: {sigma_rad} um, sigma': {sigma_rad_prime} urad
    at 3rd harmonic: sigma: {sigma_rad3} um, sigma': {sigma_rad_prime3} urad
    at 5th harmonic: sigma: {sigma_rad5} um, sigma': {sigma_rad_prime5} urad
    
Sizes and divergences of photon source (convolution) at resonance (1st harmonic): :
    Sx: {Sx} um
    Sy: {Sy} um,
    Sx': {Sxp} urad
    Sy': {Syp} urad
    
Approximated coherent fraction at 1st harmonic: 
    Horizontal: {CF_h}
    Vertical: {CF_v} 
    Coherent fraction 2D (HxV): {CF} 

"""

    def get_magnetic_structure(self, check_for_wiggler=False):
        
        if not(check_for_wiggler):
            return Undulator(K_horizontal=self.K_horizontal,
                             K_vertical=self.K_vertical,
                             period_length=self.period_length,
                             number_of_periods=self.number_of_periods)
        else:
            
            id_name = self.get_id_list()[self.elettra_id_index]
            
            if "W" in id_name:
                
                return Wiggler(K_horizontal=self.K_horizontal,
                                 K_vertical=self.K_vertical,
                                 period_length=self.period_length,
                                 number_of_periods=self.number_of_periods)
            else:
                return Undulator(K_horizontal=self.K_horizontal,
                                 K_vertical=self.K_vertical,
                                 period_length=self.period_length,
                                 number_of_periods=self.number_of_periods)


    def check_magnetic_structure_instance(self, magnetic_structure):
        if not isinstance(magnetic_structure, Undulator):
            raise ValueError("Magnetic Structure is not a Undulator")

    def populate_magnetic_structure(self):
        # if magnetic_structure is None:
        index = self.elettra_id_index- 1
        self.K_horizontal = numpy.round(self.data_dict["Kmax_hor"][index],4)
        if numpy.isnan(self.K_horizontal):
            self.K_horizontal = 0.0
        self.K_vertical = numpy.round(self.data_dict["Kmax_ver"][index],4)
        self.period_length = numpy.round(self.data_dict["id_period"][index],4)
        self.number_of_periods = numpy.round(self.data_dict["id_num_period"][index],3)

    def set_bl(self):
        
        if self.elettra_bl_index!=0:

            self.elettra_id_index = self.elettra_bl_index
                
            self.set_id()


    def set_id(self):

        if self.elettra_id_index!=0:
            
            self.populate_magnetic_structure()
            self.gap_min = self.data_dict["id_minimum_gap_mm"][self.elettra_id_index-1]
            self.gap_mm = self.data_dict["id_minimum_gap_mm"][self.elettra_id_index-1]
            
            if 'LS' in self.data_dict["position"][self.elettra_id_index-1]:
                self.set_ls_electron_beam()
            elif 'SS' in self.data_dict["position"][self.elettra_id_index-1]:
                self.set_ss_electron_beam()
            else:
                raise RuntimeError("ERROR: Unable to read source position")
            self.elettra_bl_index = self.elettra_id_index    
        self.update()

    def set_K(self):        
        self.update()

    def auto_set_undulator_V(self):
        self.set_resonance_energy(VERTICAL)

    def auto_set_undulator_H(self):
        self.set_resonance_energy(HORIZONTAL)

    def auto_set_undulator_B(self):
        self.set_resonance_energy(BOTH)

    def set_resonance_energy(self, which=VERTICAL):
        congruence.checkStrictlyPositiveNumber(self.auto_energy, "Set Undulator at Energy")
        congruence.checkStrictlyPositiveNumber(self.auto_harmonic_number, "As Harmonic #")
        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV, "Energy")
        congruence.checkStrictlyPositiveNumber(self.period_length, "Period Length")
        

        wavelength = self.auto_harmonic_number*m2ev/self.auto_energy
        K = round(numpy.sqrt(2*(((wavelength*2*self.gamma()**2)/self.period_length)-1)), 6)


        if which == VERTICAL:
            self.K_vertical = K
            self.K_horizontal = 0.0

        if which == BOTH:
            Kboth = round(K / numpy.sqrt(2), 6)
            self.K_vertical =  Kboth
            self.K_horizontal = Kboth

        if which == HORIZONTAL:
            self.K_horizontal = K
            self.K_vertical = 0.0
        
        self.update()  

    def gamma(self):
        return 1e9*self.electron_energy_in_GeV / (codata.m_e *  codata.c**2 / codata.e)

    def set_visible(self):
        self.left_box_2_1.setVisible(self.type_of_properties == 0)
        self.left_box_2_2.setVisible(self.type_of_properties == 1)
        self.left_box_2_3.setVisible(self.type_of_properties == 2)

    def check_data(self):
        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV , "Energy")
        congruence.checkStrictlyPositiveNumber(self.electron_energy_spread, "Energy Spread")
        congruence.checkStrictlyPositiveNumber(self.ring_current, "Ring Current")
        
        if self.type_of_properties == 0:
            congruence.checkPositiveNumber(self.moment_xx   , "Moment xx")
            congruence.checkPositiveNumber(self.moment_xpxp , "Moment xpxp")
            congruence.checkPositiveNumber(self.moment_yy   , "Moment yy")
            congruence.checkPositiveNumber(self.moment_ypyp , "Moment ypyp")
        elif self.type_of_properties == 1:
            congruence.checkPositiveNumber(self.electron_beam_size_h       , "Horizontal Beam Size")
            congruence.checkPositiveNumber(self.electron_beam_divergence_h , "Vertical Beam Size")
            congruence.checkPositiveNumber(self.electron_beam_size_v       , "Horizontal Beam Divergence")
            congruence.checkPositiveNumber(self.electron_beam_divergence_v , "Vertical Beam Divergence")
        elif self.type_of_properties == 2:
            congruence.checkPositiveNumber(self.electron_beam_emittance_h, "Horizontal Beam Emittance")
            congruence.checkPositiveNumber(self.electron_beam_emittance_v, "Vertical Beam Emittance")
            congruence.checkNumber(self.electron_beam_alpha_h, "Horizontal Beam Alpha")
            congruence.checkNumber(self.electron_beam_alpha_v, "Vertical Beam Alpha")
            congruence.checkNumber(self.electron_beam_beta_h, "Horizontal Beam Beta")
            congruence.checkNumber(self.electron_beam_beta_v, "Vertical Beam Beta")
            congruence.checkNumber(self.electron_beam_eta_h, "Horizontal Beam Dispersion Eta")
            congruence.checkNumber(self.electron_beam_eta_v, "Vertical Beam Dispersion Eta")
            congruence.checkNumber(self.electron_beam_etap_h, "Horizontal Beam Dispersion Eta'")
            congruence.checkNumber(self.electron_beam_etap_v, "Vertical Beam Dispersion Eta'")

        self.check_magnetic_structure()

    def send_data(self):
        self.update()
        try:
            self.check_data()
            self.send("SynedData", Beamline(light_source=self.get_light_source(check_for_wiggler=True)))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

            self.setStatusMessage("")
            self.progressBarFinished()

    def get_electron_beam(self):
        electron_beam = ElectronBeam(energy_in_GeV=self.electron_energy_in_GeV,
                                     energy_spread=self.electron_energy_spread,
                                     current=self.ring_current,
                                     number_of_bunches=self.number_of_bunches)

        if self.type_of_properties == 0:
            electron_beam.set_moments_horizontal(self.moment_xx,self.moment_xxp,self.moment_xpxp)
            electron_beam.set_moments_vertical(self.moment_yy, self.moment_yyp, self.moment_ypyp)

        elif self.type_of_properties == 1:
            electron_beam.set_sigmas_all(sigma_x=self.electron_beam_size_h,
                                         sigma_y=self.electron_beam_size_v,
                                         sigma_xp=self.electron_beam_divergence_h,
                                         sigma_yp=self.electron_beam_divergence_v)

        elif self.type_of_properties == 2:
            electron_beam.set_twiss_horizontal(self.electron_beam_emittance_h,
                                             self.electron_beam_alpha_h,
                                             self.electron_beam_beta_h)
            electron_beam.set_dispersion_horizontal(self.electron_beam_eta_h,
                                                   self.electron_beam_etap_h)
            electron_beam.set_twiss_vertical(self.electron_beam_emittance_v,
                                             self.electron_beam_alpha_v,
                                             self.electron_beam_beta_v)
            electron_beam.set_dispersion_vertical(self.electron_beam_eta_v,
                                                   self.electron_beam_etap_v)
                                             

        elif self.type_of_properties == 3:
            electron_beam.set_moments_all(0,0,0,0,0,0)

        return electron_beam

    def get_light_source(self, check_for_wiggler=False):
        return LightSource(name=self.get_id_list()[self.elettra_id_index],
                           electron_beam = self.get_electron_beam(),
                           magnetic_structure = self.get_magnetic_structure(check_for_wiggler=check_for_wiggler))

    def callResetSettings(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Reset of the Fields?"):
            try:
                self.resetSettings()
            except:
                pass

    def populate_electron_beam(self, electron_beam=None):
        if electron_beam is None:
            electron_beam = ElectronBeam(
                                        energy_in_GeV = 2.4,
                                        energy_spread = 0.000934,
                                        current = 0.4,
                                        number_of_bunches = 1,
                                        moment_xx   = (3.01836e-05)**2,
                                        moment_xxp  = (0.0)**2,
                                        moment_xpxp = (4.36821e-06)**2,
                                        moment_yy   = (3.63641e-06)**2,
                                        moment_yyp  = (0.0)**2,
                                        moment_ypyp = (1.37498e-06)**2,
                                        )

        self.electron_energy_in_GeV = electron_beam._energy_in_GeV
        self.electron_energy_spread = electron_beam._energy_spread
        self.ring_current = electron_beam._current
        self.number_of_bunches = electron_beam._number_of_bunches

        self.type_of_properties = 1

        self.moment_xx   = electron_beam._moment_xx
        self.moment_xxp  = electron_beam._moment_xxp
        self.moment_xpxp = electron_beam._moment_xpxp
        self.moment_yy   = electron_beam._moment_yy
        self.moment_yyp  = electron_beam._moment_yyp
        self.moment_ypyp = electron_beam._moment_ypyp

        x, xp, y, yp = electron_beam.get_sigmas_all()

        self.electron_beam_size_h = x
        self.electron_beam_size_v = y
        self.electron_beam_divergence_h = xp
        self.electron_beam_divergence_v = yp

    def calculate_B_from_gap_and_A_vector(self, id_gap_mm, id_period_mm, id_name,
                       a0=None, a1=None, a2=None, a3=None, a4=None, a5=None, a6=None,
                       check_elliptical=True):
        
        #TODO: Implement the parametrization of B

        if check_elliptical:
            if "EU" in id_name:
                ConfirmDialog.confirmed(self, message="Helical/Apple undulators not implemented in this app (wrong results)")
        if id_gap_mm != 'fixed':
            if "IVU" in id_name:
                B  = a0 * numpy.exp(a1 * id_gap_mm / id_period_mm)
                B += a0 * numpy.exp(a2 * (id_gap_mm / id_period_mm)**2)            
    
            elif "EU" in id_name:  # this is for apple undulator... It is applied also (WRONG!) to helical undulators
                reference_gap = 20.0
                B = a0 * numpy.exp(-numpy.pi * (id_gap_mm - reference_gap) / id_period_mm)
            else:
                if (a2 is None) and (a3 is None): # only one "harmonic"
                    B = a0 * numpy.exp(-numpy.pi * a1 * id_gap_mm / id_period_mm)
                else:
                    if (a4 is None) and (a5 is None):  # 2 "harmonics"
                        B =  a0 * numpy.exp(-numpy.pi * a2 * 1 * id_gap_mm / id_period_mm)
                        B += a1 * numpy.exp(-numpy.pi * a3 * 2 * id_gap_mm / id_period_mm)
                    else: # 3 harmonics
                        B =  a0 * numpy.exp(-numpy.pi * a3 * 1 * id_gap_mm / id_period_mm)
                        B += a1 * numpy.exp(-numpy.pi * a4 * 2 * id_gap_mm / id_period_mm)
                        B += a2 * numpy.exp(-numpy.pi * a5 * 3 * id_gap_mm / id_period_mm)
        
        elif id_gap_mm == 'fixed':

            pass

        return B

    def get_data_dictionary_csv(self):
        """ Here we read the CSV file to get the different properties of each
        Elettra 2.0 id source """
        url = self.data_url
        
        try:
            csvfile = url
            
            df = pandas.read_csv(csvfile)
            number_of_ids = len(df)
            position = df['Position']
            beamline_name = df['Beamline']
            naming = df['Naming']
            id_name = df['Name']            
            id_period = 1e-3 * df['Period']
            id_period_mm = df['Period']
            id_num_period = df['Nper']
            id_length = df['Length (m)']
            id_minimum_gap_mm = df['Min. gap (mm)']

            for i in range(number_of_ids):
                if id_minimum_gap_mm[i] is None:
                    id_minimum_gap_mm[i] = 30.0 # set to arbitrary value ** Some values are missing!!!**

            a0 = df['a0']
            a1 = df['a1']
            a2 = df['a2']
            a3 = df['a3']
            a4 = df['a4']
            a5 = df['a5']
            a6 = df['a6']


            Bmax_ver = df['By_peak(T)']
            Bmax_hor = df['Bx_peak(T)']
            Kmax_ver = df['Max_Ky']
            Kmax_hor = df['Max_Kx']
            # TODO: Not yet implemented #
            #for i in range(number_of_ids):
            #    Bmax_i = self.calculate_B_from_gap_and_A_vector(
            #        id_minimum_gap_mm[i], id_period_mm[i], id_name[i],
            #        a0=a0[i], a1=a1[i], a2=a2[i], a3=a3[i], a4=a4[i], a5=a5[i], a6=a5[i],
            #        check_elliptical=False)
            #    Bmax.append(Bmax_i)
            #    Kmax.append(Bmax_i * id_period[i] * codata.e / (2 * numpy.pi * codata.m_e * codata.c))

            out_dict = {}
            out_dict["position"] = position.to_list()
            out_dict["beamline_name"] = beamline_name.to_list()
            out_dict["id_name"] = id_name.to_list()
            out_dict["id_minimum_gap_mm"] = id_minimum_gap_mm.to_list()
            out_dict["Bmax_ver"] = Bmax_ver.to_list()
            out_dict["Bmax_hor"] = Bmax_hor.to_list()
            out_dict["Kmax_ver"] = Kmax_ver.to_list()
            out_dict["Kmax_hor"] = Kmax_hor.to_list()
            out_dict["position"] = position.to_list()
            out_dict["naming"] = naming.to_list()
            out_dict["id_period"] = id_period.to_list()
            out_dict["id_period_mm"] = id_period_mm.to_list()
            out_dict["id_length"] = id_length.to_list()
            out_dict["id_num_period"] = id_num_period.to_list()
            out_dict["a0"] = a0.to_list()
            out_dict["a1"] = a1.to_list()
            out_dict["a2"] = a2.to_list()
            out_dict["a3"] = a3.to_list()
            out_dict["a4"] = a4.to_list()
            out_dict["a5"] = a5.to_list()
            out_dict["a6"] = a6.to_list()

        except:
            print("Something went wrong while reading the file")
            out_dict = {}
            out_dict["position"] =          [] 
            out_dict["beamline_name"] =     []
            out_dict["id_name"] =           []
            out_dict["id_minimum_gap_mm"] = [] 
            out_dict["Bmax_ver"] =          []
            out_dict["Bmax_hor"] =          []
            out_dict["Kmax_ver"] =          []
            out_dict["Kmax_hor"] =          []
            out_dict["position"] =          []
            out_dict["naming"] =            []
            out_dict["id_period"] =         []
            out_dict["id_period_mm"] =      []
            out_dict["id_length"] =         []
            out_dict["id_num_period"] =     []
            out_dict["a0"] =                []
            out_dict["a1"] =                []
            out_dict["a2"] =                []
            out_dict["a3"] =                []
            out_dict["a4"] =                []
            out_dict["a5"] =                []
            out_dict["a6"] =                []  

        self.data_dict = out_dict

    # Long Straigth Section electron parameters
    def get_ls_electronbeam(self):
        file_url = self.data_ls       
        elettra_ls = load_from_json_file(file_url)             
        self.ls_electronbeam = elettra_ls.get_electron_beam()
    # Short Straigth Section electron parameters
    def get_ss_electronbeam(self):
        file_url = self.data_ss
        #print("Reading SS e-beam from file: ", file_url)       
        elettra_ss = load_from_json_file(file_url)            
        self.ss_electronbeam = elettra_ss.get_electron_beam()
        #print(self.ss_electronbeam.get_dispersion_all())
        #print(self.ss_electronbeam.get_moments_all())

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    a = QApplication(sys.argv)
    ow = OWELETTRA2()
    ow.show()
    a.exec_()