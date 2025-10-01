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
}

if (typeof module !== 'undefined') {
    module.exports = DAACSCharts;
}
