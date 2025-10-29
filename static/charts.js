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
        container.append('p').text('Navigation data ready. Integrate tangles visualization here.');
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
            row.forEach(cell => tr.append('td').text(cell));
        });
    }
}

if (typeof module !== 'undefined') {
    module.exports = DAACSCharts;
}
