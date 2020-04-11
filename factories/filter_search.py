from enums.item_types import ItemTypes
from search_filters.consumables_filters import ConsumablesFilteredSearch
from search_filters.custom_filters import CustomFiltersSearch
from search_filters.filtered_search_by_name import NameFilteredSearch


class FilterSearchFactory:
    def __init__(self, item, player_custom_filters=None):
        self.item = item
        self.player_custom_filters = player_custom_filters

    def get_filter_search_class(self):
        if ItemTypes.PLAYER == ItemTypes(self.item.type):
            if not self.player_custom_filters:
                return NameFilteredSearch()
            else:
                return CustomFiltersSearch()
        return ConsumablesFilteredSearch()