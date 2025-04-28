from wagtail.core.models import Page
from wagtail.admin.edit_handlers import FieldPanel

class BlogPage(Page):
    introduction = models.TextField()

    content_panels = Page.content_panels + [
        FieldPanel('introduction'),
    ]
