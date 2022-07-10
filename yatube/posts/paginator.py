from django.core.paginator import Paginator


PAGE_SELECTION: int = 10


def get_page(post_list, request):
    paginator = Paginator(post_list, PAGE_SELECTION)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
