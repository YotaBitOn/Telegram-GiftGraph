

const configForm = document.getElementById('config-form');
if (configForm) {
    configForm.addEventListener('submit', (e) => {
        e.preventDefault();
        connectToServer();
    });
}

visited_users = [];
queued_users = new Set();
const linksData = [];
const width = 1920;
const height = 1080;
const nodesData = [{ 
    id: "Target User", 
    x: width / 2, 
    y: height / 2 - 200, 
    fx: width / 2, 
    fy: height / 2 - 200, 
    isInitial: true 
}];


let startingUsername = "";

async function add_node(name  = null, gifters = []) {
    let node_name, target_name, target_index;

    if (name != null) {
        name = name.toString().replace(/^@/, '').trim();
        gifters = gifters.map(g => typeof g === 'string' ? g.replace(/^@/, '').trim() : g);
    }

    if (name == null){
        let visited = new Set();

        console.log("No name provided");

        node_name = "Note " + nodesData.length;

        visited_users.push(node_name);

        let its_targets = Math.floor( Math.random()*(nodesData.length/200))
        if (its_targets == 0) its_targets = 1;

        console.log("With target ammo : " + its_targets);

        for (let i = 0; i < its_targets; i++) {
            do{
                target_index = Math.floor( Math.random()*(visited_users.length-1));
            } while(visited.has(target_index))
            visited.add(target_index);



            target_name = visited_users[target_index];
            console.log("Adding link: " + node_name + " -> " + target_name);
            linksData.push({ source: node_name, target: target_name });


        }
    }
    else {
        node_name = name;
        console.log("Is array:", Array.isArray(gifters), "Length:", gifters?.length);
        for (const gifter of gifters) {
            if (!queued_users.has(gifter)) {
                queued_users.add(gifter);
                nodesData.push({ 
                    id: gifter,
                    x: width / 2 + (Math.random() - 0.5) * 200,
                    y: height / 2 + (Math.random() - 0.5) * 200
                });
            }
            console.log("Adding link: " + node_name + " -> " + gifter);
            linksData.push({ source: node_name, target: gifter });
        }
    }

    console.log("Adding node: " + node_name);
    console.log('\n\n\n');

    if (!queued_users.has(node_name)) {
        queued_users.add(node_name);
        nodesData.push({ 
            id: node_name,
            x: width / 2 + (Math.random() - 0.5) * 200,
            y: height / 2 + (Math.random() - 0.5) * 200
        });
    }

    // Refresh data bindings
    links = container.selectAll("line")
        .data(linksData)
        .join(
            enter => enter.append("line")
                .attr("stroke", "#999")
                .attr("stroke-width", 1)
                .attr("stroke-opacity", 0.6)
                .each(d => d.t = 0)
                .call(enter => enter.transition().duration(1000)
                    .tween("extend", d => {
                        const i = d3.interpolate(0, 1);
                        return t => { d.t = i(t); };
                    })),
            update => update,
            exit => exit.remove()
        );

    nodes = container.selectAll("circle")
        .data(nodesData, d => d.id)
        .join(
            enter => enter.append("circle")
                .attr("r", 16)
                .attr("fill", "#7b2eda")
                .style("opacity", 0)
                .call(enter => enter.transition().duration(1000).style("opacity", 1)),
            update => update,
            exit => exit.remove()
        )
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    labels = container.selectAll("text")
        .data(nodesData, d => d.id)
        .join(
            enter => enter.append("text")
                .style("opacity", 0)
                .call(enter => enter.transition().duration(1000).style("opacity", 1)),
            update => update,
            exit => exit.remove()
        )
        .text(d => d.isInitial ? "" : d.id)
        .attr("font-size", "16px")
        .attr("dx", 20)
        .attr("dy", ".35em")
        .attr("fill", "#ccc");

    simulation.nodes(nodesData);
    simulation.force("link").links(linksData);
    
    simulation.alpha(1).restart();

    // Auto-zoom if graph outgrows viewport
    const bounds = nodesData.reduce((acc, d) => {
        if (d.x < acc.minX) acc.minX = d.x;
        if (d.x > acc.maxX) acc.maxX = d.x;
        if (d.y < acc.minY) acc.minY = d.y;
        if (d.y > acc.maxY) acc.maxY = d.y;
        return acc;
    }, { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });

    const margin = 50;
    if (bounds.minX < margin || bounds.maxX > width - margin || 
        bounds.minY < margin || bounds.maxY > height - margin) {
        zoomToFit(800);
    }
}


const zoom = d3.zoom()
    .scaleExtent([0.05, 5])
    .on("zoom", (event) => {
        container.attr("transform", event.transform);
    });

let svg = d3.select("body").append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet")
    .call(zoom);

const container = svg.append("g");

function zoomToFit(transitionDuration = 500) {
    if (nodesData.length === 0) return;

    // Calculate bounds
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodesData.forEach(d => {
        if (d.x < minX) minX = d.x;
        if (d.x > maxX) maxX = d.x;
        if (d.y < minY) minY = d.y;
        if (d.y > maxY) maxY = d.y;
    });

    // Add padding
    const padding = 200;
    minX -= padding;
    maxX += padding;
    minY -= padding;
    maxY += padding;

    const graphWidth = maxX - minX;
    const graphHeight = maxY - minY;
    
    // Calculate scale to fit within 1920x1080
    const scale = Math.min(width / graphWidth, height / graphHeight, 1) * 0.8;
    
    // Calculate center translation
    const tx = (width - graphWidth * scale) / 2 - minX * scale;
    const ty = (height - graphHeight * scale) / 2 - minY * scale;

    const transform = d3.zoomIdentity.translate(tx, ty).scale(scale);

    if (transitionDuration > 0) {
        svg.transition().duration(transitionDuration).call(zoom.transform, transform);
    } else {
        svg.call(zoom.transform, transform);
    }
}

let links = container.append("g")
    .selectAll("line")
    .data(linksData)
    .join(
        enter => enter.append("line")
            .attr("stroke", "#999")
            .attr("stroke-width", 1)
            .attr("stroke-opacity", 0.6)
            .each(d => d.t = 0)
            .call(enter => enter.transition().duration(1000)
                .tween("extend", d => {
                    const i = d3.interpolate(0, 1);
                    return t => { d.t = i(t); };
                })),
        update => update,
        exit => exit.remove()
    );


let nodes = container.append("g")
    .selectAll("circle")
    .data(nodesData, d => d.id)
    .join(
        enter => enter.append("circle")
            .attr("r", 16)
            .attr("fill", "#7b2eda")
            .style("opacity", 0)
            .call(enter => enter.transition().duration(1000).style("opacity", 1)),
        update => update,
        exit => exit.remove()
    )
    .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    let labels = container.selectAll("text")
        .data(nodesData, d => d.id)
        .join(
            enter => enter.append("text")
                .style("opacity", 0)
                .call(enter => enter.transition().duration(1000).style("opacity", 1)),
            update => update,
            exit => exit.remove()
        )
        .text(d => d.isInitial ? "" : d.id)
        .attr("font-size", "16px")
        .attr("dx", 20)
        .attr("dy", ".35em")
        .attr("fill", "#ccc");

const simulation = d3.forceSimulation(nodesData)
    .force("link", d3.forceLink(linksData).id(d => d.id).distance(105))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(20));



simulation.on("tick", () => {
    links
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.source.x + (d.target.x - d.source.x) * (d.t || 1))
        .attr("y2", d => d.source.y + (d.target.y - d.source.y) * (d.t || 1));

    nodes
        .attr("cx", d => d.x)
        .attr("cy", d => d.y);

    labels
        .attr("x", d => d.x)
        .attr("y", d => d.y);
});


function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}


async function connectToServer(){
    const usernameInput = document.getElementById('tg-id').value.replace('@', '').trim();
    const depth = parseInt(document.getElementById('depth').value);
    const limit = parseInt(document.getElementById('user-limit').value);

    if (!usernameInput) {
        alert("Please enter a username");
        return;
    }
    startingUsername = usernameInput;

    const initialNode = nodesData.find(n => n.isInitial);
    if (initialNode) {
        initialNode.id = startingUsername;
        initialNode.isInitial = false;
        queued_users.add(startingUsername);

        // Smooth slide to center
        d3.transition()
            .duration(1000)
            .ease(d3.easeCubicInOut)
            .tween("move", () => {
                const ix = d3.interpolate(initialNode.fx, width / 2);
                const iy = d3.interpolate(initialNode.fy, height / 2);
                return (t) => {
                    initialNode.fx = ix(t);
                    initialNode.fy = iy(t);
                };
            })
            .on("end", () => {
                initialNode.fx = null;
                initialNode.fy = null;
            });

        add_node(startingUsername, []);
    }

    // Hide the config container with animation
    const mainContainer = document.querySelector('.main-container');
    if (mainContainer) {
        mainContainer.classList.add('fade-out');
    }

    const ws = new WebSocket("ws://localhost:8765");

    ws.onopen = () => {
        ws.send(JSON.stringify({
            USERNAME: startingUsername,
            MAX_DEPTH: depth,
            MAX_USERS: limit,
            DELAY: 1.0,
        }));
    };

    ws.onmessage = (event) => {
        const datum = JSON.parse(event.data);

        if (datum.__done) {
            console.log("Stream complete", datum);
            // Final zoom out to see everything
            zoomToFit(1500);
            setTimeout(() => {
                showStatusNotification(datum);
                ws.close();
            }, 3000);
            return;
        }

        console.log(datum);

        // Handle initial user node transition from handle to display name
        if (datum.handle === startingUsername && datum.user !== startingUsername) {
            const node = nodesData.find(n => n.id === startingUsername);
            if (node) {
                console.log(`Renaming initial node from ${startingUsername} to ${datum.user}`);
                const oldId = startingUsername;
                const newId = datum.user;
                
                node.id = newId;
                queued_users.delete(oldId);
                queued_users.add(newId);
                
                // Update links that might already refer to the old handle
                linksData.forEach(l => {
                    if (l.source === oldId) l.source = newId;
                    if (l.target === oldId) l.target = newId;
                    // If they are already objects, d3 will use the reference which is already updated
                });
            }
        }

        if (visited_users.includes(datum.user)) return;
        visited_users.push(datum.user);
        add_node(datum.user, datum.gifters)
    };

    ws.onerror = (e) => {
        console.error("WS error:", e);
        showStatusNotification({ __done: true, errors: ["Connection lost or server error"], visited_count: visited_users.length });
    };
    ws.onclose = () => console.log("WS closed");
}

function showStatusNotification(data) {
    const notification = document.getElementById('status-notification');
    const title = document.getElementById('status-title');
    const message = document.getElementById('status-message');
    const errorList = document.getElementById('error-list');
    
    if (!notification) return;

    errorList.innerHTML = '';
    const count = data.visited_count ?? visited_users.length;
    
    if (data.errors && data.errors.length > 0) {
        title.innerText = "Parsing finished with some issues";
        title.style.color = "#ffcc00";
        message.innerText = `Visited ${count} users. The following issues occurred:`;
        errorList.style.display = 'block';
        
        const ul = document.createElement('ul');
        // Limit errors shown to avoid huge list
        const displayErrors = data.errors.slice(0, 5);
        displayErrors.forEach(err => {
            const li = document.createElement('li');
            li.innerText = err;
            ul.appendChild(li);
        });
        if (data.errors.length > 5) {
            const li = document.createElement('li');
            li.innerText = `... and ${data.errors.length - 5} more.`;
            ul.appendChild(li);
        }
        errorList.appendChild(ul);
    } else {
        title.innerText = "Parsing Complete!";
        title.style.color = "#00ff00";
        message.innerText = `Successfully visited ${count} users without errors.`;
        errorList.style.display = 'none';
    }

    notification.classList.remove('hidden');
    notification.classList.add('fade-in');

    document.getElementById('close-notification').onclick = () => {
        notification.classList.add('hidden');
        notification.classList.remove('fade-in');
    };
}
