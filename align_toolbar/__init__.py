from .align_actions import icon_path, run_action, start_order_tracker
import pcbnew


TOOLS = [
    ("left", "Align to Left", "Seçili öğeleri sola hizala"),
    ("hcenter", "Align to Horizontal Center", "Seçili öğeleri yatay merkeze hizala"),
    ("right", "Align to Right", "Seçili öğeleri sağa hizala"),
    ("top", "Align to Top", "Seçili öğeleri üste hizala"),
    ("vcenter", "Align to Vertical Center", "Seçili öğeleri dikey merkeze hizala"),
    ("bottom", "Align to Bottom", "Seçili öğeleri alta hizala"),
    ("dist_h_gaps", "Distribute Horizontally with Even Gaps", "Yatayda eşit boşlukla dağıt"),
    ("dist_v_gaps", "Distribute Vertically with Even Gaps", "Dikeyde eşit boşlukla dağıt"),
]


def _make_plugin(action, name, description):
    class AlignToolbarPlugin(pcbnew.ActionPlugin):
        def defaults(self):
            self.name = name
            self.category = "Align/Distribute"
            self.description = description
            self.show_toolbar_button = True
            self.icon_file_name = icon_path(action, False)
            self.dark_icon_file_name = icon_path(action, True)

        def Run(self):
            run_action(action)

    AlignToolbarPlugin.__name__ = "AlignToolbar_" + action
    return AlignToolbarPlugin()


for tool in TOOLS:
    _make_plugin(*tool).register()

start_order_tracker()
# AI
