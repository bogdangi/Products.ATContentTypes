import simplejson as json
from zope.i18n import translate
from Acquisition import aq_inner
from Products.Five.browser import BrowserView

class JSONCriteriaForField(BrowserView):
    """Return the criteria vocabulary as a json result"""
    
    def __call__(self):
        vocab = self.context.allowedCriteriaForField(self.request['field'],
            display_list=True)
        
        self.request.response.setHeader(
            'Content-Type', 'application/json; charset=utf-8')
        return json.dumps([
            dict(
                value=item, 
                label=translate(vocab.getValue(item), self.request)
            ) for item in vocab
        ])
