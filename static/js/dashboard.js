/*
 * JKC Supermarket — staff dashboard: the revenue chart on the overview page.
 * Plain JavaScript and inline SVG, no chart library.
 *
 * The page provides (see templates/supermarket/dashboard/overview.html):
 *
 *   <script id="revenue-chart-data" type="application/json">   {bucket, points[], has_data}
 *   data-chart-card                      the card; holds everything below
 *   data-revenue-chart                   empty box the SVG is drawn into (its CSS height includes the x labels)
 *   data-chart-view / data-chart-table   the chart and the server-rendered table of the same numbers
 *   data-chart-toggle                    button that switches between the two
 *
 * Without JavaScript the table is what shows, so the chart never has to be the
 * only way to read a value. Styles are the chart-* classes in frontend/src/app.css.
 */
(function () {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const MAX_COLUMN_WIDTH = 24;
  const SEGMENT_GAP = 2;
  const CORNER_RADIUS = 4;
  const X_LABEL_BAND = 28;
  // Labels are thinned to every Nth column; these keep N a number people expect.
  const LABEL_STEPS = { day: [1, 2, 5, 10, 15], week: [1, 2, 4, 8], month: [1, 2, 3, 4, 6, 12] };

  const SERIES = [
    { field: 'total', name: 'Total', key: '' },
    { field: 'goods', name: 'Goods sales', key: 'chart-key-goods' },
    { field: 'delivery', name: 'Delivery fees', key: 'chart-key-delivery' },
  ];

  function svgEl(name, attrs) {
    const node = document.createElementNS(SVG_NS, name);
    Object.keys(attrs || {}).forEach((key) => node.setAttribute(key, attrs[key]));
    return node;
  }

  function htmlEl(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function money(value) {
    return '$' + Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function axisMoney(value, step) {
    const digits = step % 1 === 0 ? 0 : 2;
    return '$' + value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  /* A round step (1, 2, 2.5 or 5 times a power of ten) and the first tick at or above the tallest column. */
  function niceScale(max, intervals) {
    if (!(max > 0)) return { step: 1, top: intervals };
    const raw = max / intervals;
    const power = Math.pow(10, Math.floor(Math.log10(raw)));
    const fraction = raw / power;
    let nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
    // $250 is a round number, $2.50 on an axis is not.
    if (power >= 10 && fraction > 2 && fraction <= 2.5) nice = 2.5;
    const step = nice * power;
    return { step: step, top: Math.ceil(max / step - 1e-9) * step };
  }

  function roundedTopPath(x, y, width, height) {
    const r = Math.max(0, Math.min(CORNER_RADIUS, width / 2, height));
    const right = x + width;
    const bottom = y + height;
    return 'M' + x + ',' + bottom + 'V' + (y + r) + 'Q' + x + ',' + y + ' ' + (x + r) + ',' + y +
      'H' + (right - r) + 'Q' + right + ',' + y + ' ' + right + ',' + (y + r) + 'V' + bottom + 'Z';
  }

  function pointTitle(point, bucket) {
    if (bucket === 'week') return 'Week of ' + point.label;
    if (bucket === 'day' && point.start) {
      // No "Z": the date is a local calendar day, not a UTC instant.
      const day = new Date(point.start + 'T00:00:00');
      if (!isNaN(day)) return day.toLocaleDateString('en-US', { weekday: 'short' }) + ' ' + point.label;
    }
    return point.label;
  }

  function hasKeyboardFocus(node) {
    try {
      return node.matches(':focus-visible');
    } catch (e) {
      return false; // a browser without :focus-visible
    }
  }

  function ordersText(count) {
    return count + (count === 1 ? ' order' : ' orders');
  }

  function readChartData() {
    const source = document.getElementById('revenue-chart-data');
    if (!source) return null;
    try {
      const data = JSON.parse(source.textContent);
      return data && Array.isArray(data.points) && data.points.length ? data : null;
    } catch (e) {
      return null;
    }
  }

  function initRevenueChart() {
    const plot = document.querySelector('[data-revenue-chart]');
    const data = readChartData();
    if (!plot || !data) return null;

    const points = data.points;
    const bucket = LABEL_STEPS[data.bucket] ? data.bucket : 'day';
    const maxTotal = points.reduce((max, point) => Math.max(max, point.total || 0), 0);

    const tooltip = htmlEl('div', 'chart-tooltip');
    // Each column's aria-label already says everything the tooltip shows.
    tooltip.setAttribute('aria-hidden', 'true');
    const tooltipTitle = htmlEl('p', 'chart-tooltip-title');
    tooltip.appendChild(tooltipTitle);
    const tooltipValues = SERIES.concat([{ field: 'orders', name: 'Orders', key: '' }]).map((series) => {
      const row = htmlEl('p', 'chart-tooltip-row');
      row.appendChild(htmlEl('span', ('chart-tooltip-key ' + series.key).trim()));
      const value = row.appendChild(htmlEl('span', 'chart-tooltip-value'));
      row.appendChild(htmlEl('span', '', series.name));
      tooltip.appendChild(row);
      return { field: series.field, node: value };
    });
    plot.appendChild(tooltip);

    let svg = null;
    let columns = [];
    let geometry = null;
    let drawnSize = '';
    let active = -1;
    let tabStop = 0;
    let animate = true;

    function deactivate() {
      if (active >= 0 && columns[active]) {
        columns[active].band.classList.remove('is-active');
        columns[active].bars.classList.remove('is-active');
      }
      active = -1;
      tooltip.classList.remove('is-visible');
    }

    function activate(index) {
      if (!columns[index]) return;
      if (index !== active) {
        deactivate();
        active = index;
        columns[index].band.classList.add('is-active');
        columns[index].bars.classList.add('is-active');
      }

      const point = points[index];
      tooltipTitle.textContent = pointTitle(point, bucket);
      tooltipValues.forEach((entry) => {
        entry.node.textContent = entry.field === 'orders' ? String(point.orders || 0) : money(point[entry.field] || 0);
      });

      // Beside the column rather than over it, on whichever side has room.
      const column = columns[index];
      const offset = geometry.columnWidth / 2 + 10;
      let x = column.centre + offset;
      if (x + tooltip.offsetWidth > geometry.width) x = column.centre - offset - tooltip.offsetWidth;
      x = clamp(x, 0, Math.max(0, geometry.width - tooltip.offsetWidth));
      const y = clamp(column.top - tooltip.offsetHeight / 2, 0, Math.max(0, geometry.baseline - tooltip.offsetHeight));
      tooltip.style.transform = 'translate(' + Math.round(x) + 'px,' + Math.round(y) + 'px)';
      tooltip.classList.add('is-visible');
    }

    /* One tab stop for the whole chart; the arrow keys move along the columns. */
    function moveTabStop(index, focus) {
      tabStop = clamp(index, 0, columns.length - 1);
      columns.forEach((column, i) => column.hit.setAttribute('tabindex', i === tabStop ? '0' : '-1'));
      if (focus) columns[tabStop].hit.focus();
    }

    function onKeyDown(event) {
      const index = columns.findIndex((column) => column.hit === event.currentTarget);
      const target = { ArrowLeft: index - 1, ArrowRight: index + 1, Home: 0, End: columns.length - 1 }[event.key];
      if (target !== undefined) {
        event.preventDefault();
        moveTabStop(target, true);
      } else if (event.key === 'Escape') {
        deactivate();
      }
    }

    function indexFromPointer(event) {
      const x = event.clientX - svg.getBoundingClientRect().left - geometry.left;
      return clamp(Math.floor(x / geometry.slot), 0, columns.length - 1);
    }

    function draw(force) {
      const width = plot.clientWidth;
      const height = plot.clientHeight;
      // No size means the table view is showing; the observer redraws when the chart comes back.
      if (!width || !height) return;
      const size = width + 'x' + height;
      if (size === drawnSize && !force) return;
      drawnSize = size;

      const hadFocus = svg && svg.contains(document.activeElement);
      deactivate();
      // A hidden tooltip left out at the old right-hand edge would widen the page once the card shrinks.
      tooltip.style.transform = '';
      if (svg) svg.remove();

      svg = svgEl('svg', { width: width, height: height, role: 'group' });
      svg.setAttribute('aria-label', plot.getAttribute('data-chart-label') || 'Revenue chart');
      if (animate) svg.classList.add('chart-animate');
      plot.insertBefore(svg, tooltip);

      const top = 10;
      const baseline = height - X_LABEL_BAND;
      const plotHeight = baseline - top;
      const scale = niceScale(maxTotal, plotHeight < 220 ? 3 : 4);
      const perDollar = plotHeight / scale.top;

      // Bands sit under the grid lines so a highlighted column keeps its grid.
      const bands = svg.appendChild(svgEl('g'));
      const grid = svg.appendChild(svgEl('g'));

      // Y labels go in before anything is placed: the widest one decides where the plot area starts.
      const tickLabels = [];
      for (let value = 0; value <= scale.top + scale.step / 2; value += scale.step) {
        const label = svgEl('text', { class: 'chart-axis-text', 'text-anchor': 'end', 'dominant-baseline': 'middle' });
        label.textContent = axisMoney(value, scale.step);
        svg.appendChild(label);
        tickLabels.push({ node: label, y: Math.round(baseline - value * perDollar) });
      }
      // The web font may still be loading and is a little wider than the fallback, hence the slack.
      const left = Math.ceil(tickLabels.reduce((max, tick) => Math.max(max, tick.node.getComputedTextLength()), 0)) + 14;
      const right = 4;
      const slot = (width - left - right) / points.length;
      const columnWidth = clamp(Math.floor(slot * 0.62), 2, MAX_COLUMN_WIDTH);
      geometry = { width: width, left: left, slot: slot, baseline: baseline, columnWidth: columnWidth };

      tickLabels.forEach((tick) => {
        tick.node.setAttribute('x', left - 8);
        tick.node.setAttribute('y', tick.y);
        // Half-pixel offset keeps a 1px line on one row of pixels.
        grid.appendChild(svgEl('line', { class: 'chart-grid-line', x1: left, x2: width - right, y1: tick.y + 0.5, y2: tick.y + 0.5 }));
      });

      const bars = svg.appendChild(svgEl('g'));
      const labels = svg.appendChild(svgEl('g'));
      const hits = svg.appendChild(svgEl('g'));

      columns = points.map((point, i) => {
        const centre = left + (i + 0.5) * slot;
        const x = Math.round(centre - columnWidth / 2);

        const band = bands.appendChild(svgEl('rect', { class: 'chart-band', x: left + i * slot, y: top, width: slot, height: plotHeight }));

        let goodsHeight = point.goods > 0 ? Math.max(1, point.goods * perDollar) : 0;
        let deliveryHeight = point.delivery > 0 ? Math.max(1, point.delivery * perDollar) : 0;
        if (goodsHeight && deliveryHeight) {
          // The white gap comes out of the two segments, so the stack still ends at the total.
          goodsHeight = Math.max(1, goodsHeight - SEGMENT_GAP / 2);
          deliveryHeight = Math.max(1, deliveryHeight - SEGMENT_GAP / 2);
        }
        const goodsY = baseline - goodsHeight;
        const deliveryY = goodsY - (goodsHeight ? SEGMENT_GAP : 0) - deliveryHeight;

        const group = bars.appendChild(svgEl('g', { class: 'chart-bars' }));
        group.style.transformOrigin = '0px ' + baseline + 'px';
        group.style.animationDelay = Math.min(i * 12, 360) + 'ms';
        // Only the segment on top of the stack gets the rounded end; everything is square at the baseline.
        if (goodsHeight && deliveryHeight) {
          group.appendChild(svgEl('rect', { class: 'chart-bar chart-bar-goods', x: x, y: goodsY, width: columnWidth, height: goodsHeight }));
        } else if (goodsHeight) {
          group.appendChild(svgEl('path', { class: 'chart-bar chart-bar-goods', d: roundedTopPath(x, goodsY, columnWidth, goodsHeight) }));
        }
        if (deliveryHeight) {
          group.appendChild(svgEl('path', { class: 'chart-bar chart-bar-delivery', d: roundedTopPath(x, deliveryY, columnWidth, deliveryHeight) }));
        }

        // The hit target is the whole slot, top to bottom, so short and empty columns are as easy to read as tall ones.
        const hit = hits.appendChild(svgEl('rect', { class: 'chart-hit', x: left + i * slot, y: 0, width: slot, height: height, role: 'img' }));
        hit.setAttribute('aria-label', pointTitle(point, bucket) + ': total ' + money(point.total || 0) +
          ', goods sales ' + money(point.goods || 0) + ', delivery fees ' + money(point.delivery || 0) +
          ', ' + ordersText(point.orders || 0));
        hit.addEventListener('focus', () => { moveTabStop(i, false); activate(i); });
        hit.addEventListener('blur', deactivate);
        hit.addEventListener('keydown', onKeyDown);

        return { band: band, bars: group, hit: hit, centre: centre, top: deliveryHeight ? deliveryY : goodsY };
      });

      // X labels: every Nth column counting back from the newest, so the latest date is always named.
      const probe = labels.appendChild(svgEl('text', { class: 'chart-axis-text' }));
      probe.textContent = points.reduce((longest, point) => (String(point.label).length > longest.length ? String(point.label) : longest), '');
      const labelWidth = probe.getComputedTextLength();
      probe.remove();
      const needed = Math.ceil((labelWidth + 16) / slot);
      const steps = LABEL_STEPS[bucket];
      let every = steps.find((step) => step >= needed) || needed;
      if (bucket === 'day' && points.length > 14) every = Math.max(every, 5);
      for (let i = points.length - 1; i >= 0; i -= every) {
        const label = labels.appendChild(svgEl('text', { class: 'chart-axis-text', 'text-anchor': 'middle', y: baseline + 19 }));
        label.textContent = points[i].label;
        const half = label.getComputedTextLength() / 2 + 3;
        label.setAttribute('x', clamp(columns[i].centre, half, width - half));
      }

      svg.addEventListener('pointermove', (event) => activate(indexFromPointer(event)));
      svg.addEventListener('pointerdown', (event) => activate(indexFromPointer(event)));
      svg.addEventListener('pointerleave', (event) => {
        // A finger lifting is not "leaving": keep the tooltip until the next tap elsewhere.
        if (event.pointerType !== 'mouse') return;
        // Back to the column the keyboard is on, if there is one.
        if (svg.contains(document.activeElement) && hasKeyboardFocus(document.activeElement)) activate(tabStop);
        else deactivate();
      });

      moveTabStop(tabStop, hadFocus);
      animate = false;
    }

    document.addEventListener('pointerdown', (event) => {
      if (!plot.contains(event.target)) deactivate();
    });

    let frame = 0;
    const scheduleDraw = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => draw(false));
    };
    if ('ResizeObserver' in window) new ResizeObserver(scheduleDraw).observe(plot);
    else window.addEventListener('resize', scheduleDraw);
    draw(true);

    return { redraw: scheduleDraw };
  }

  function initViewToggle(chart) {
    const card = document.querySelector('[data-chart-card]');
    if (!card) return;
    const button = card.querySelector('[data-chart-toggle]');
    const view = card.querySelector('[data-chart-view]');
    const table = card.querySelector('[data-chart-table]');
    if (!button || !view || !table) return;

    // The table is the no-JavaScript fallback; from here on this script decides which one shows.
    table.classList.remove('js-hidden');
    // No chart to switch to (its data is missing): leave the table up on its own.
    if (!chart) {
      view.hidden = true;
      button.hidden = true;
      return;
    }
    table.hidden = true;

    const icon = button.querySelector('i');
    const label = button.querySelector('[data-chart-toggle-label]');
    button.addEventListener('click', () => {
      const showTable = table.hidden;
      table.hidden = !showTable;
      view.hidden = showTable;
      // The button names the view it switches to.
      if (label) label.textContent = showTable ? 'Chart' : 'Table';
      if (icon) {
        icon.classList.toggle('fa-table', !showTable);
        icon.classList.toggle('fa-chart-column', showTable);
      }
      if (!showTable) chart.redraw();
    });
  }

  function init() {
    initViewToggle(initRevenueChart());
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
