
  import DataTable from 'datatables.net-dt';
  import 'datatables.net-dt/css/dataTables.dataTables.css';
  import 'datatables.net-scroller-dt';
  import 'datatables.net-scroller-dt/css/scroller.dataTables.css';

  window.createDataTable = function(el) {
    const data = JSON.parse(el.querySelector('script').textContent)
    new DataTable(el.querySelector('table'), {
      data,
      scroller: true,
      scrollCollapse: true,
      scrollY: 500,
      searching: false,
      order: []
    });
  }
