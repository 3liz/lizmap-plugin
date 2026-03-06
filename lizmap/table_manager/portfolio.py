""" Table manager for Portfolio. """

from lizmap.table_manager.base import TableManager


class TableManagerPortfolio(TableManager):

    """ Table manager for Portfolio.

    Set the label dictionnary list to: list
    """

    @staticmethod
    def label_dictionary_list() -> str:
        """ The label in the CFG file prefixing the list. """
        return "list"
