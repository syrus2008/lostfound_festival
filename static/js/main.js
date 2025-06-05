$(document).ready(function() {
  $('#itemForm').on('submit', function(e) {
    e.preventDefault();
    let form = $(this);
    let titre = $('input[name="title"]').val();
    let categoryId = $('select[name="category"]').val();

    if (!titre || !categoryId) {
      form.off('submit').submit();
      return;
    }

    $.ajax({
      url: '/api/check_similar',
      method: 'POST',
      data: {
        title: titre,
        category_id: categoryId
      },
      success: function(response) {
        if (response.similars && response.similars.length > 0) {
          let doublonList = $('#doublonList');
          doublonList.empty();
          response.similars.forEach(function(item) {
            doublonList.append(
              `<li><a href="/item/${item.id}" target="_blank">
                ${item.title} (score ${item.score}%)
              </a></li>`
            );
          });
          let modal = new bootstrap.Modal(document.getElementById('doublonModal'));
          modal.show();

          $('#confirmSubmit').off('click').on('click', function() {
            modal.hide();
            form.off('submit').submit();
          });
        } else {
          form.off('submit').submit();
        }
      },
      error: function() {
        form.off('submit').submit();
      }
    });
  });
});
