/**
 * DAACS Analytics D3.js Charts Library
 * 
 * This library provides D3.js chart implementations for DAACS analytics data.
 * Compatible with the D3 Graph Gallery patterns: https://d3-graph-gallery.com/
 */

class DAACSCharts {
    constructor() {
        this.width = 640;
        this.height = 360;
        this.margin = { top: 20, right: 20, bottom: 40, left: 50 };
    }

    createScoreDistribution(containerId, data) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();

        const distribution = (data && data.score_distribution) || [];
        if (!distribution.length) {
            container.append('p').text('No distribution data available');
            return;
        }

        const width = this.width - this.margin.left - this.margin.right;
        const height = this.height - this.margin.top - this.margin.bottom;

        const svg = container
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        const x = d3.scaleBand()
            .domain(distribution.map(d => d.range))
            .range([0, width])
            .padding(0.2);

        const y = d3.scaleLinear()
            .domain([0, d3.max(distribution, d => d.count) || 1])
            .range([height, 0]);

        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x));

        svg.append('g').call(d3.axisLeft(y));

        svg.selectAll('.bar')
            .data(distribution)
            .enter()
            .append('rect')
            .attr('class', 'bar')
            .attr('x', d => x(d.range))
            .attr('y', d => y(d.count))
            .attr('width', x.bandwidth())
            .attr('height', d => height - y(d.count))
            .attr('fill', '#2563eb');
    }

    renderTrafficLight(containerId, indicator) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        const dots = indicator?.dots || ['gray', 'gray', 'gray'];
        const svg = container.append('svg').attr('width', 120).attr('height', 40);
        svg.selectAll('circle')
            .data(dots)
            .enter()
            .append('circle')
            .attr('cx', (_, i) => 20 + i * 35)
            .attr('cy', 20)
            .attr('r', 12)
            .attr('fill', color => ({ green: '#22c55e', yellow: '#facc15', red: '#ef4444', gray: '#d1d5db' }[color] || '#d1d5db'));
    }

    createBarChart(containerId, data, config = {}) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        const series = data || [];
        if (!series.length) {
            container.append('p').text(config.emptyMessage || 'No data available');
            return;
        }
        const width = this.width - this.margin.left - this.margin.right;
        const height = this.height - this.margin.top - this.margin.bottom;
        const svg = container.append('svg').attr('width', this.width).attr('height', this.height).append('g').attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        const x = d3.scaleBand().domain(series.map(d => d.label || d.date)).range([0, width]).padding(0.1);
        const y = d3.scaleLinear().domain([0, d3.max(series, d => d.value || d.count) || 1]).range([height, 0]);
        svg.append('g').attr('transform', `translate(0,${height})`).call(d3.axisBottom(x).tickFormat(config.tickFormat || (d => d)));
        svg.append('g').call(d3.axisLeft(y));
        svg.selectAll('.bar').data(series).enter().append('rect').attr('class', 'bar').attr('x', d => x(d.label || d.date)).attr('y', d => y(d.value || d.count)).attr('width', x.bandwidth()).attr('height', d => height - y(d.value || d.count)).attr('fill', config.color || '#2563eb');
    }

    createCircularBarplot(containerId, data) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        const series = data || [];
        if (!series.length) {
            container.append('p').text('No data available');
            return;
        }
        const width = 500;
        const height = 500;
        const innerRadius = 120;
        const outerRadius = Math.min(width, height) / 2;
        const svg = container.append('svg').attr('width', width).attr('height', height).append('g').attr('transform', `translate(${width / 2},${height / 2})`);
        const angle = d3.scaleBand().domain(series.map(d => d.questionId || d.label)).range([Math.PI / 2, 2.5 * Math.PI]);
        const radius = d3.scaleLinear().domain([0, d3.max(series, d => d.count || d.value)]).range([innerRadius, outerRadius]);
        svg.selectAll('path').data(series).enter().append('path').attr('fill', '#6366f1').attr('d', d3.arc().innerRadius(innerRadius).outerRadius(d => radius(d.count || d.value)).startAngle(d => angle(d.questionId || d.label)).endAngle(d => angle(d.questionId || d.label) + angle.bandwidth()));
    }

    renderNavigationTree(containerId, events) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();

        if (!events || !events.length) {
            container.append('div').attr('class', 'empty').text('No navigation events in this range.');
            return;
        }

        const maxSteps = 60;
        const steps = events.slice(0, maxSteps).map((event, idx) => {
            const label = event.title || event.url || `Step ${idx + 1}`;
            const timestamp = event.timestamp ? new Date(event.timestamp).toLocaleString() : '';
            return {
                id: `${idx}-${label}`,
                label,
                url: event.url,
                timestamp,
                depth: idx,
            };
        });

        const columns = [];
        steps.forEach(node => {
            if (!columns[node.depth]) {
                columns[node.depth] = [];
            }
            columns[node.depth].push(node);
        });

        const columnWidth = 160; // tighter spacing
        const rowHeight = 80;
        const margin = { top: 36, right: 80, bottom: 56, left: 80 };
        const radius = 10;

        const width = margin.left + columnWidth * Math.max(1, columns.length - 1) + margin.right;
        const maxRows = Math.max(...columns.map(col => (col ? col.length : 0)));
        const height = margin.top + rowHeight * Math.max(1, maxRows) + margin.bottom;

        columns.forEach((col, colIdx) => {
            if (!col) return;
            col.forEach((node, rowIdx) => {
                node.x = margin.left + colIdx * columnWidth;
                node.y = margin.top + rowIdx * rowHeight;
            });
        });

        const links = [];
        for (let i = 1; i < steps.length; i += 1) {
            links.push({ source: steps[i - 1], target: steps[i] });
        }

        container.style('overflow-x', 'auto');
        const svg = container.append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const defs = svg.append('defs');
        const gradient = defs.append('linearGradient')
            .attr('id', 'nav-tangle-gradient')
            .attr('x1', '0%')
            .attr('y1', '0%')
            .attr('x2', '100%')
            .attr('y2', '0%');
        gradient.append('stop').attr('offset', '0%').attr('stop-color', '#6366f1');
        gradient.append('stop').attr('offset', '100%').attr('stop-color', '#22d3ee');

        const link = d3.linkHorizontal()
            .x(d => d.x)
            .y(d => d.y);

        svg.append('g')
            .attr('fill', 'none')
            .attr('stroke-width', 2.3)
            .attr('stroke-linecap', 'round')
            .selectAll('path')
            .data(links)
            .enter()
            .append('path')
            .attr('stroke', 'url(#nav-tangle-gradient)')
            .attr('opacity', (d, idx) => Math.max(0.3, 1 - (idx / steps.length) * 0.6))
            .attr('d', d => link({
                source: [d.source.x + radius, d.source.y],
                target: [d.target.x - radius, d.target.y],
            }));

        const nodes = svg.append('g')
            .selectAll('g.node')
            .data(steps)
            .enter()
            .append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${d.x}, ${d.y})`);

        nodes.append('circle')
            .attr('r', radius)
            .attr('fill', '#0f172a')
            .attr('stroke', '#22d3ee')
            .attr('stroke-width', 2);

        nodes.append('text')
            .attr('x', 0)
            .attr('y', -16)
            .attr('fill', '#f8fafc')
            .attr('font-size', 13)
            .attr('font-weight', 600)
            .attr('text-anchor', 'middle')
            .text(d => (d.label && d.label.length > 28) ? `${d.label.slice(0, 28)}…` : d.label);

        nodes.append('text')
            .attr('x', 0)
            .attr('y', 24)
            .attr('fill', '#94a3b8')
            .attr('font-size', 11)
            .attr('text-anchor', 'middle')
            .text(d => d.timestamp || (d.url ? d.url.slice(0, 50) : ''));

        const legend = svg.append('g')
            .attr('transform', `translate(${margin.left}, ${height - margin.bottom + 20})`);

        legend.append('text')
            .attr('fill', '#94a3b8')
            .attr('font-size', 12)
            .text(`Showing ${steps.length} steps${events.length > steps.length ? ` (of ${events.length})` : ''}`);
    }

    renderPairsTable(containerId, rows, headers) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        if (!rows.length) {
            container.append('div').attr('class', 'empty').text('No data available.');
            return;
        }
        const table = container.append('table').attr('class', 'data-table');
        const thead = table.append('thead').append('tr');
        headers.forEach(header => thead.append('th').text(header));
        const tbody = table.append('tbody');
        rows.forEach(row => {
            const tr = tbody.append('tr');
            row.forEach(cell => {
                const td = tr.append('td');
                if (typeof cell === 'string' && cell.includes('<')) {
                    td.html(cell);
                } else {
                    td.text(cell);
                }
            });
        });
    }

    createMonthDayHeatmap(containerId, buckets, config = {}) {
        const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        const data = buckets || [];
        if (!data.length) {
            container.append('div').attr('class', 'empty').text('No login events in this range.');
            return;
        }

        const cellSize = 24;
        const daysMax = 31;
        const width = months.length * cellSize + this.margin.left + this.margin.right;
        const height = daysMax * cellSize + this.margin.top + this.margin.bottom;

        const svg = container
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        const x = d3.scaleBand().domain(d3.range(1, 13)).range([0, months.length * cellSize]).padding(0.05);
        const y = d3.scaleBand().domain(d3.range(1, daysMax + 1)).range([0, daysMax * cellSize]).padding(0.05);
        const maxCount = d3.max(data, d => d.count) || 1;
        const color = d3.scaleSequential(d3.interpolateYlGnBu).domain([0, maxCount]);

        svg.selectAll('rect.cell')
            .data(data)
            .enter()
            .append('rect')
            .attr('class', 'cell')
            .attr('x', d => x(d.month))
            .attr('y', d => y(d.day))
            .attr('width', x.bandwidth())
            .attr('height', y.bandwidth())
            .attr('rx', 3)
            .attr('ry', 3)
            .attr('fill', d => color(d.count || 0))
            .append('title')
            .text(d => `${months[d.month-1]} ${d.day}: ${d.count}`);

        svg.append('g')
            .attr('transform', `translate(0, ${daysMax * cellSize})`)
            .call(d3.axisBottom(x).tickFormat(m => months[m-1]))
            .selectAll('text')
            .style('font-size', 11);

        svg.append('g')
            .call(d3.axisLeft(y).tickValues([1,5,10,15,20,25,30]))
            .selectAll('text')
            .style('font-size', 11);

        // Legend
        const legendWidth = 160, legendHeight = 10;
        const legend = svg.append('g')
            .attr('transform', `translate(${months.length*cellSize - legendWidth}, -10)`);
        const legendScale = d3.scaleLinear().domain([0, maxCount]).range([0, legendWidth]);
        const gradientId = 'heatmapGradient';
        const defs = svg.append('defs');
        const grad = defs.append('linearGradient').attr('id', gradientId);
        grad.append('stop').attr('offset', '0%').attr('stop-color', color(0));
        grad.append('stop').attr('offset', '100%').attr('stop-color', color(maxCount));
        legend.append('rect').attr('width', legendWidth).attr('height', legendHeight).attr('fill', `url(#${gradientId})`);
        legend.append('g').attr('transform', `translate(0, ${legendHeight})`).call(d3.axisBottom(legendScale).ticks(4)).selectAll('text').style('font-size', 10);
        legend.append('text').attr('x', legendWidth + 6).attr('y', legendHeight - 2).attr('fill', '#94a3b8').attr('font-size', 11).text('Logins');
    }

    createMonthWeekdayHeatmap(containerId, buckets) {
        const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
        const weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]; // Monday=0
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        const data = buckets || [];
        if (!data.length) {
            container.append('div').attr('class', 'empty').text('No login events for this year.');
            return;
        }
        const cell = 26;
        const width = months.length * cell + this.margin.left + this.margin.right;
        const height = weekdays.length * cell + this.margin.top + this.margin.bottom;
        const svg = container.append('svg').attr('width', width).attr('height', height)
            .append('g').attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        const x = d3.scaleBand().domain(d3.range(1, 13)).range([0, months.length * cell]).padding(0.05);
        const y = d3.scaleBand().domain(d3.range(0, 7)).range([0, weekdays.length * cell]).padding(0.05);
        const maxCount = d3.max(data, d => d.count) || 1;
        const color = d3.scaleSequential(d3.interpolateYlGnBu).domain([0, maxCount]);
        svg.selectAll('rect').data(data).enter().append('rect')
            .attr('x', d => x(d.month))
            .attr('y', d => y(d.weekday))
            .attr('width', x.bandwidth()).attr('height', y.bandwidth())
            .attr('rx', 3).attr('ry', 3)
            .attr('fill', d => color(d.count || 0))
            .append('title').text(d => `${weekdays[d.weekday]} ${months[d.month-1]}: ${d.count}`);
        svg.append('g').attr('transform', `translate(0, ${weekdays.length * cell})`).call(d3.axisBottom(x).tickFormat(m => months[m-1])).selectAll('text').style('font-size', 11).attr('transform','rotate(45)').style('text-anchor','start');
        svg.append('g').call(d3.axisLeft(y).tickFormat(w => weekdays[w])).selectAll('text').style('font-size', 11);
    }

    createDotChartDaily(containerId, series) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        const data = series || [];
        const days = data.length || 31;
        if (!data.length) {
            container.append('div').attr('class', 'empty').text('No data available.');
            return;
        }
        const width = this.width + this.margin.left + this.margin.right;
        const height = 300;
        const svg = container.append('svg').attr('width', width).attr('height', height);
        const g = svg.append('g').attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        const innerWidth = width - this.margin.left - this.margin.right;
        const innerHeight = height - this.margin.top - this.margin.bottom;
        const x = d3.scaleLinear().domain([1, days]).range([0, innerWidth]);
        const y = d3.scaleLinear().domain([0, d3.max(data, d => d.count) || 1]).nice().range([innerHeight, 0]);
        const ticks = d3.range(1, days + 1);
        const xAxis = g.append('g')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(d3.axisBottom(x).tickValues(ticks).tickFormat(d => d).tickSizeOuter(0));
        xAxis.selectAll('text').style('font-size', 10);
        g.append('g').call(d3.axisLeft(y));
        g.selectAll('circle')
            .data(data)
            .enter()
            .append('circle')
            .attr('cx', d => x(d.day))
            .attr('cy', d => y(d.count))
            .attr('r', 2.5)
            .attr('fill', '#60a5fa')
            .attr('stroke', '#0f172a')
            .attr('stroke-width', 0.6)
            .append('title')
            .text(d => `Day ${d.day}: ${d.count}`);

        const line = d3.line()
            .x(d => x(d.day))
            .y(d => y(d.count))
            .curve(d3.curveMonotoneX);
        g.append('path')
            .datum(data)
            .attr('fill', 'none')
            .attr('stroke', '#3b82f6')
            .attr('stroke-width', 1.5)
            .attr('d', line);
    }

    createRidgeline(containerId, labels, seriesMap) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        // Start with provided order, but filter out labels with insufficient data
        const categoriesRaw = labels || Object.keys(seriesMap || {});
        const baseFilter = (label) => {
            const arr = (seriesMap[label] || []).map(n => +n).filter(n => !Number.isNaN(n));
            if (arr.length < 2) return false; // need at least two samples for KDE
            const unique = new Set(arr);
            return unique.size >= 2; // exclude degenerate single-value series
        };
        const nonOption = categoriesRaw.filter(label => String(label).toLowerCase() !== 'option').filter(baseFilter);
        const categories = nonOption.length ? nonOption : categoriesRaw.filter(baseFilter);
        if (categories.length < 1) {
            container.append('div').attr('class', 'empty').text('No data available.');
            return;
        }

        // Collect all numeric values and compute a robust upper bound (to avoid 1 big outlier flattening curves)
        const allValues = [];
        categories.forEach(k => (seriesMap[k] || []).forEach(v => {
            const n = +v; if (!Number.isNaN(n)) allValues.push(n);
        }));
        const sorted = allValues.slice().sort(d3.ascending);
        const q = (p) => (sorted.length ? d3.quantile(sorted, p) : undefined);
        let xMax = q(0.98) || d3.max(allValues) || 1;
        if (!xMax || xMax <= 0) xMax = 1;

        // Layout tuned to mimic Seaborn ridgeline aesthetics
        const rowHeight = 34; // compact rows so curves overlap a bit
        const width = this.width + 80; // a bit wider for labels
        const height = 24 + categories.length * rowHeight + 24;
        const margin = { top: 10, right: 24, bottom: 36, left: 160 };
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const svg = container.append('svg').attr('width', width).attr('height', height);
        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const x = d3.scaleLinear().domain([0, xMax]).nice().range([0, innerWidth]);
        const y = d3.scaleBand().domain(categories).range([0, innerHeight]).padding(0.18);

        // Coolwarm-like palette across rows (blue to red)
        const color = d3.scaleSequential()
            .domain([categories.length - 1, 0]) // reverse so first is blue-ish
            .interpolator(d3.interpolateRdYlBu);

        // Proper Epanechnikov kernel with bandwidth scaling
        function epanechnikovKernel(bw) {
            return function (u) {
                const x = u / bw;
                return Math.abs(x) <= 1 ? 0.75 * (1 - x * x) / bw : 0;
            };
        }
        function kernelDensityEstimator(kernel, X, V) {
            return V.map(v => [v, d3.mean(X, x0 => kernel(v - x0))]);
        }

        // Silverman-ish bandwidth heuristic
        const mean = d3.mean(allValues) || 0;
        const sd = Math.sqrt(d3.variance(allValues) || 0) || (xMax / 8);
        const n = Math.max(2, allValues.length);
        const bwSilverman = 1.06 * sd * Math.pow(n, -1/5);
        const bandwidth = Math.max(0.5, Math.min(xMax / 6, bwSilverman || xMax / 10));
        const samples = 120;
        const step = xMax / samples;
        const sampleX = d3.range(0, xMax + step, step);

        // X axis only (clean ridgeline look)
        g.append('g')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(d3.axisBottom(x).ticks(6))
            .call(ax => ax.selectAll('text').style('font-size', 11).style('font-weight', 600));

        // Draw each ridge
        categories.forEach((cat, idx) => {
            const raw = (seriesMap[cat] || []).map(n => +n).filter(n => !Number.isNaN(n)).map(v => Math.min(v, xMax));
            if (!raw.length) return;

            const density = kernelDensityEstimator(epanechnikovKernel(bandwidth), raw, sampleX);
            const yCenter = (y(cat) ?? 0) + y.bandwidth() / 2;
            const amplitude = rowHeight * 0.55; // bigger than half-band -> slight overlap
            const yScale = d3.scaleLinear()
                .domain([0, d3.max(density, d => d[1]) || 1])
                .range([0, amplitude]);

            // Area (filled)
            const area = d3.area()
                .curve(d3.curveBasis)
                .x(d => x(d[0]))
                .y0(yCenter)
                .y1(d => yCenter - yScale(d[1]));

            // Contour (white stroke on top)
            const contour = d3.line()
                .curve(d3.curveBasis)
                .x(d => x(d[0]))
                .y(d => yCenter - yScale(d[1]));

            const fillColor = color(idx);

            // Baseline
            g.append('line')
                .attr('x1', x(0))
                .attr('x2', x(xMax))
                .attr('y1', yCenter)
                .attr('y2', yCenter)
                .attr('stroke', '#cbd5e1')
                .attr('stroke-width', 1)
                .attr('opacity', 0.6);

            // Ridge area
            g.append('path')
                .datum(density)
                .attr('fill', fillColor)
                .attr('fill-opacity', 0.85)
                .attr('stroke', 'none')
                .attr('d', area);

            // White contour
            g.append('path')
                .datum(density)
                .attr('fill', 'none')
                .attr('stroke', '#ffffff')
                .attr('stroke-width', 1.6)
                .attr('d', contour)
                .attr('paint-order', 'stroke');

            // Category label to the left, colored like the ridge
            g.append('text')
                .attr('x', -10)
                .attr('y', yCenter + 4)
                .attr('text-anchor', 'end')
                .attr('fill', fillColor)
                .style('font-weight', 700)
                .text(cat);
        });

        // Clean look: no y-axis, no frame
    }
}

if (typeof module !== 'undefined') {
    module.exports = DAACSCharts;
}
