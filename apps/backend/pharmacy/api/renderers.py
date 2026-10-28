from decimal import Decimal
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class DecimalStringEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return format(obj, "f")
        return super().default(obj)


class FinancialJSONRenderer(JSONRenderer):
    encoder_class = DecimalStringEncoder
