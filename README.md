# MongoDBShardingExample

An example of MongoDB sharding using Docker and Python.

> **Prerequisites:**  
> - **Docker** and **docker-compose** must be installed and properly configured.  
> - **MongoDB** (via Docker images) must be accessible.  
> - In Python, install the required packages listed in `requirements.txt`.

---

## Overview

This project demonstrates how to set up a sharded MongoDB cluster using Docker containers and how to interact with the sharded data via Python. In this example, the cluster consists of:

- **Config Servers:** A three-member replica set (`cfgrs`) for cluster metadata.
- **Shards:** Three distinct shards, each implemented as a replica set with two members.  
  - **shard1rs:** Two nodes (mainly used for system collections, such as `config.system.sessions`).
  - **shard2rs** and **shard3rs:** Two nodes each, used for storing application data in the `exampleDB.files` collection.
- **Mongos Router:** A single mongos process that routes queries to the appropriate shard(s).

---

## Procedure

### 1. Boot Up the Docker Containers

Run the following command in the directory containing your `docker-compose.yml` file:

```sh
docker-compose up -d
```

This command starts all services (config servers, shard replica sets, and the mongos router) in detached mode.

---

### 2. Initialize the Config Server Replica Set (`cfgrs`)

Open a shell into one of the config server containers (e.g., `configs1`):

```sh
docker exec -it configs1 mongosh --port 27017
```

Then, initialize the replica set by executing:

```javascript
rs.initiate({
  _id: "cfgrs",
  configsvr: true,
  members: [
    { _id: 0, host: "configs1:27017" },
    { _id: 1, host: "configs2:27017" },
    { _id: 2, host: "configs3:27017" }
  ]
})
```

Wait until the replica set initialization completes successfully.

---

### 3. Initialize the Shard Replica Sets

#### For Shard 1 (`shard1rs`):

Connect to one of the shard1 containers:

```sh
docker exec -it shard1s1 mongosh --port 27017
```

Initialize the shard replica set:

```javascript
rs.initiate({
  _id: "shard1rs",
  members: [
    { _id: 0, host: "shard1s1:27017" },
    { _id: 1, host: "shard1s2:27017" }
  ]
})
```

#### For Shard 2 (`shard2rs`):

Connect to one of the shard2 containers:

```sh
docker exec -it shard2s1 mongosh --port 27017
```

Initialize the replica set:

```javascript
rs.initiate({
  _id: "shard2rs",
  members: [
    { _id: 0, host: "shard2s1:27017" },
    { _id: 1, host: "shard2s2:27017" }
  ]
})
```

#### For Shard 3 (`shard3rs`):

Connect to one of the shard3 containers:

```sh
docker exec -it shard3s1 mongosh --port 27017
```

Initialize the replica set:

```javascript
rs.initiate({
  _id: "shard3rs",
  members: [
    { _id: 0, host: "shard3s1:27017" },
    { _id: 1, host: "shard3s2:27017" }
  ]
})
```

Wait until each shard replica set is fully initialized.

---

### 4. Add the Shards to the Cluster via Mongos

First, connect to the mongos container:

```sh
docker exec -it mongos mongosh --port 27017
```

Then, add each shard to the cluster:

```javascript
sh.addShard("shard1rs/shard1s1:27017,shard1s2:27017")
sh.addShard("shard2rs/shard2s1:27017,shard2s2:27017")
sh.addShard("shard3rs/shard3s1:27017,shard3s2:27017")
```

To verify that the shards were added correctly, run:

```javascript
sh.status()
```

You should see all three shards listed along with their respective configuration details.

---

### 5. Enable Sharding on the Application Database

In the mongos shell, execute the following commands to enable sharding on your target database and shard the collection:

```javascript
// Enable sharding on the 'exampleDB' database.
sh.enableSharding("exampleDB")

// Shard the 'files' collection on the 'filename' field.
sh.shardCollection("exampleDB.files", { filename: 1 })
```

MongoDB will now manage the `exampleDB.files` collection by splitting its data into chunks based on the `filename` shard key. As data grows or chunk splits/migrations occur, the balancer will distribute the data among the available shards.

---

## Note

After running your Python program (`main.py`) repeatedly (which inserts documents and performs queries), the output of `sh.status()` in the mongos shell might look similar to the following JSON excerpt:

```json
databases
[
  {
    database: { _id: 'config', primary: 'config', partitioned: true },
    collections: {
      'config.system.sessions': {
        shardKey: { _id: 1 },
        unique: false,
        balancing: true,
        chunkMetadata: [ { shard: 'shard1rs', nChunks: 1 } ],
        chunks: [
          { min: { _id: MinKey() }, max: { _id: MaxKey() }, 'on shard': 'shard1rs', 'last modified': Timestamp({ t: 1, i: 0 }) }
        ],
        tags: []
      }
    }
  },
  {
    database: {
      _id: 'exampleDB',
      primary: 'shard3rs',
      version: {
        uuid: UUID('8884af4d-21e0-47c5-984c-35a5d3b46611'),
        timestamp: Timestamp({ t: 1738569282, i: 2 }),
        lastMod: 1
      }
    },
    collections: {
      'exampleDB.files': {
        shardKey: { filename: 1 },
        unique: false,
        balancing: true,
        chunkMetadata: [
          { shard: 'shard2rs', nChunks: 1 },
          { shard: 'shard3rs', nChunks: 1 }
        ],
        chunks: [
          { min: { filename: MinKey() }, max: { filename: '53aae26ed6e52b77447c0246957de2f490f16aefb6032993e92ab96c0983188fe2821509b5acc9af19cbb4c37f356df5e027ca89b86cb4bffa8dc3900260526402237c080a64413201f32eb333ca0d53cb22ddbcf74ca0e876b0db97692b1e485d1ee74939632096d9e911efd5ba06f985fa1c3534fab9a3e111531f096714d2.jpg' }, 'on shard': 'shard2rs', 'last modified': Timestamp({ t: 2, i: 0 }) },
          { min: { filename: '53aae26ed6e52b77447c0246957de2f490f16aefb6032993e92ab96c0983188fe2821509b5acc9af19cbb4c37f356df5e027ca89b86cb4bffa8dc3900260526402237c080a64413201f32eb333ca0d53cb22ddbcf74ca0e876b0db97692b1e485d1ee74939632096d9e911efd5ba06f985fa1c3534fab9a3e111531f096714d2.jpg' }, max: { filename: MaxKey() }, 'on shard': 'shard3rs', 'last modified': Timestamp({ t: 2, i: 1 }) }
        ],
        tags: []
      }
    }
  }
]
```

**Explanation:**

- **Data Distribution:**  
  - The `exampleDB.files` collection is split into two chunks. One chunk resides on **shard2rs** and the other on **shard3rs**.  
  - The `config.system.sessions` collection is stored on **shard1rs**. MongoDB automatically places system collections (like session data) on one of the shards.

- **Primary Shard for `exampleDB`:**  
  The primary shard for `exampleDB` is reported as **shard3rs**. This primary designation affects where unsharded collections are created and can influence initial chunk allocation for sharded collections.

- **Autosplit & Balancer:**  
  Autosplit is enabled, and the balancer is working (or has worked) to distribute data as chunks grow or are split, although in this example, most application data ended up in shard2rs and shard3rs.

---

## Summary

This documentation explains how to set up a Docker-based sharded MongoDB cluster and how to interact with it using Python. The steps include:

1. Booting the containers with `docker-compose`.
2. Initializing the config server replica set (`cfgrs`).
3. Initializing three shard replica sets (`shard1rs`, `shard2rs`, `shard3rs`) with two nodes each.
4. Adding the shards to the cluster via a mongos router.
5. Enabling sharding on the `exampleDB` database and sharding the `files` collection on the `filename` field.

The provided `sh.status()` output demonstrates how data is distributed across the shards—with system collections on **shard1rs** and application data in **exampleDB.files** split between **shard2rs** and **shard3rs**.
