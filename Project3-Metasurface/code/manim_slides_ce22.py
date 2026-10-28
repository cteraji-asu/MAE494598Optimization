"""Local CE 0.22 glue for released Manim Slides 5.7; installed files unchanged.

CE 0.22 replaced write_to_movie with format and moved cache flushing out of the
global config. The official BaseSlide still owns segmentation, reverse-media
generation and presentation configuration; the official players are unchanged.
"""
import manim
import manim_slides
from manim import Scene,config
from manim_slides import ThreeDSlide
from manim_slides.slide.base import BaseSlide

class CompatibleThreeDSlide(ThreeDSlide):
    def __init__(self,*args,**kwargs):
        if manim.__version__!='0.22.0' or manim_slides.__version__!='5.7.0':
            raise RuntimeError('Review this narrow adapter for different package versions.')
        config.format='mp4'
        # CE snapshots cache limits in the writer during scene construction.
        # Setting this only in render() is too late for decks over 100 plays.
        config.max_files_cached=-1
        BaseSlide.__init__(self,*args,**kwargs)
    def render(self,*args,**kwargs):
        previous=config.max_files_cached;config.max_files_cached=-1
        try:
            result=Scene.render(self,*args,**kwargs)
            self._save_slides(use_cache=not(config.disable_caching or self.disable_caching),flush_cache=self.flush_cache,skip_reversing=self.skip_reversing)
            return result
        finally:config.max_files_cached=previous
