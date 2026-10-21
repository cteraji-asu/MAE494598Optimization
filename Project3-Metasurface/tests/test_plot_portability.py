import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"code"))
try:
    from PIL import Image,ImageDraw
except ImportError:
    Image=None


@unittest.skipIf(Image is None,"Optional plot package Pillow is absent")
class PlotPortabilityTests(unittest.TestCase):
    def test_embedded_fallback_without_any_system_font(self):
        from plot_results import portable_font
        font=portable_font(24,candidates=["/nonexistent/fonts/no-font.ttf"])
        image=Image.new("RGB",(500,80),"white")
        ImageDraw.Draw(image).text((10,10),"Helmholtz k=10",font=font,fill="black")
        self.assertGreater(font.getbbox("Helmholtz")[2],0)
        self.assertNotEqual(image.getextrema(),((255,255),(255,255),(255,255)))


if __name__=="__main__":
    unittest.main()
