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
        let doublonList = $('#doublonList');
        doublonList.empty();
        if (response.similars && response.similars.length > 0) {
          response.similars.forEach(function(item) {
            let img = item.photo_url ? `<img src="${item.photo_url}" alt="Photo" class="rounded me-3" style="width:56px; height:56px; object-fit:cover;">` : `<div class='bg-light d-inline-flex align-items-center justify-content-center text-muted me-3' style='width:56px; height:56px; border-radius:0.375rem;'>—</div>`;
            let cat = item.category_name ? `<span class='badge bg-secondary ms-2'>${item.category_name}</span>` : '';
            doublonList.append(
              `<li class="d-flex align-items-center mb-3">
                ${img}
                <div class="flex-grow-1">
                  <a href="${item.url_detail}" target="_blank" class="fw-bold text-decoration-none">${item.title}</a>
                  ${cat}<br>
                  <span class="text-muted small">Score : ${item.score}%</span>
                </div>
              </li>`
            );
          });
          $('#doublonListContainer').show();
          $('#noDoublon').addClass('d-none');
          let modal = new bootstrap.Modal(document.getElementById('doublonModal'));
          modal.show();

          $('#confirmSubmit').off('click').on('click', function() {
            modal.hide();
            form.off('submit').submit();
          });
        } else {
          $('#doublonListContainer').hide();
          $('#noDoublon').removeClass('d-none');
          let modal = new bootstrap.Modal(document.getElementById('doublonModal'));
          modal.show();
          $('#confirmSubmit').off('click').on('click', function() {
            modal.hide();
            form.off('submit').submit();
          });
        }
      },
      error: function() {
        form.off('submit').submit();
      }
    });
  });
});
