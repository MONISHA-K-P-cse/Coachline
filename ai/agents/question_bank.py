QUESTION_BANK = {
    "DSA": {
        "Easy": [
            "What is the difference between an Array and a Linked List, and when is each preferred?",
            "Explain how a stack works and name a real-world use case for it.",
            "What is binary search, and what is its time complexity compared to linear search?"
        ],
        "Medium": [
            "Explain how hash collisions occur in a Hash Map and how separate chaining resolves them.",
            "What is the difference between Depth-First Search (DFS) and Breadth-First Search (BFS) on a graph?",
            "How do you detect a cycle in a singly linked list using two pointers?"
        ],
        "Hard": [
            "Explain how an AVL tree maintains its balance during insertions and deletions.",
            "How does Dijkstra's algorithm find the shortest path in a weighted graph, and what is its complexity?",
            "Explain the difference between Dynamic Programming (DP) and Memoization with an example."
        ],
        "Expert": [
            "Design a data structure that performs LRU Cache eviction in O(1) time for all operations.",
            "How does a Segment Tree or Fenwick Tree optimize range query updates in logarithmic time?",
            "Explain the algorithmic implementation of A* search with heuristics in pathfinding."
        ]
    },
    "DBMS": {
        "Easy": [
            "What is the difference between a Primary Key and a Foreign Key?",
            "Explain the difference between INNER JOIN and LEFT JOIN with examples.",
            "What is the purpose of database normalization?"
        ],
        "Medium": [
            "Explain the difference between a clustered and non-clustered index in SQL.",
            "What are ACID transactions, and why is the Write-Ahead Log (WAL) critical?",
            "Explain the difference between Optimistic and Pessimistic concurrency control."
        ],
        "Hard": [
            "What is database sharding, and how does it differ from horizontal replication?",
            "Explain the difference between Read Committed and Serializable transaction isolation levels.",
            "How do replica lags occur in primary-replica database setups, and how do you handle consistency?"
        ],
        "Expert": [
            "How does a database storage engine design (like B-Tree vs LSM-Tree) impact write throughput?",
            "Explain the CAP theorem and discuss how database partitioning impacts consistency vs availability.",
            "Design a distributed transaction coordination strategy using 2-Phase Commit (2PC) or Saga patterns."
        ]
    },
    "OS": {
        "Easy": [
            "What is the difference between a process and a thread?",
            "Explain the concept of virtual memory and why it is useful.",
            "What is a deadlock, and what are the four necessary conditions for it to occur?"
        ],
        "Medium": [
            "Explain the difference between preemptive and non-preemptive CPU scheduling.",
            "What is thrashing in operating systems, and how can it be prevented?",
            "Explain the difference between user mode and kernel mode in OS execution."
        ],
        "Hard": [
            "How do page replacement algorithms like LRU and FIFO work, and what is Belady's anomaly?",
            "Explain how semaphores and mutexes differ, and how they prevent race conditions.",
            "What is context switching, and what overheads are associated with it?"
        ],
        "Expert": [
            "Design a thread-safe lock-free queue using Compare-And-Swap (CAS) atomic operations.",
            "How does the Linux kernel handle virtual file system (VFS) cache page reclamation under memory pressure?",
            "Explain the differences between kernel-level threads (KLT) and user-level threads (ULT) scheduler activations."
        ]
    },
    "CN": {
        "Easy": [
            "What is the difference between TCP and UDP, and when would you use each?",
            "Explain the function of DNS in computer networks.",
            "What is the difference between HTTP and HTTPS?"
        ],
        "Medium": [
            "How does the TCP 3-way handshake establish a connection, and how is it terminated?",
            "Explain the difference between IPv4 and IPv6 addressing.",
            "What is the purpose of a Subnet Mask, and how does subnetting work?"
        ],
        "Hard": [
            "Explain the TCP congestion control mechanism, including slow start and congestion avoidance.",
            "How does SSL/TLS handshake establish a secure connection between client and server?",
            "Compare client-side load balancing with server-side load balancing in distributed networks."
        ],
        "Expert": [
            "How does HTTP/2 multiplexing work over a single TCP connection compared to HTTP/1.1 head-of-line blocking?",
            "Explain how the Border Gateway Protocol (BGP) determines routing paths across autonomous systems.",
            "Design a reliable file transfer protocol on top of raw UDP packets, handling packet loss and reordering."
        ]
    },
    "OOP": {
        "Easy": [
            "What are the four main pillars of Object-Oriented Programming?",
            "Explain the difference between a class and an object.",
            "What is the difference between method overloading and method overriding?"
        ],
        "Medium": [
            "Explain the difference between an abstract class and an interface, and when to use each.",
            "What is encapsulation, and how does it secure object states?",
            "Explain the concept of composition vs inheritance."
        ],
        "Hard": [
            "Explain the SOLID design principles with a concrete coding example for the Dependency Inversion Principle.",
            "What are design patterns, and can you compare the Factory pattern with the Abstract Factory pattern?",
            "Explain the Singleton pattern and how you would implement a thread-safe singleton in Java or C++."
        ],
        "Expert": [
            "Design an extensible plugins framework using the Dependency Injection and Strategy patterns.",
            "How do virtual method tables (vtables) resolve dynamic dispatch at runtime in compiled languages?",
            "Explain the Liskov Substitution Principle and show how subclassing a Square from a Rectangle violates it."
        ]
    },
    "System Design": {
        "Easy": [
            "What is the difference between vertical scaling and horizontal scaling?",
            "What is a load balancer, and why is it important in system architecture?",
            "What is a Content Delivery Network (CDN), and how does it reduce latency?"
        ],
        "Medium": [
            "Compare Cache-Aside, Write-Through, and Write-Back caching strategies.",
            "What is database replication, and what is the difference between synchronous and asynchronous replication?",
            "Explain the difference between monolithic and microservices architectures."
        ],
        "Hard": [
            "How do you design a distributed unique ID generator (like Snowflake) that scales across multiple servers?",
            "What is a cache stampede (thundering herd problem), and how do you mitigate it?",
            "How does a distributed rate limiter work using token bucket or sliding window algorithms?"
        ],
        "Expert": [
            "Design a distributed message queue (like Kafka) handling partition ordering and consumer group rebalances.",
            "Explain how Consistent Hashing works and how virtual nodes prevent hot spots in key-value stores.",
            "Design a global metadata search index capable of parsing and syncing updates from millions of clients."
        ]
    },
    "ML": {
        "Easy": [
            "What is the difference between supervised and unsupervised learning?",
            "Explain the difference between overfitting and underfitting in ML models.",
            "What are training, validation, and test datasets used for?"
        ],
        "Medium": [
            "Explain the bias-variance trade-off in machine learning.",
            "What is the difference between L1 (Lasso) and L2 (Ridge) regularization?",
            "Why is the ROC-AUC score preferred over classification accuracy for imbalanced datasets?"
        ],
        "Hard": [
            "How does a Random Forest model determine feature importances?",
            "Explain the vanishing gradient problem in deep neural networks and how to mitigate it.",
            "Explain the self-attention mechanism in Transformer architectures."
        ],
        "Expert": [
            "Design a high-throughput, low-latency real-time inference pipeline for deep learning models.",
            "Explain the mathematical formulation of backpropagation through time (BPTT) and its optimization limits.",
            "How do temperature and top-p sampling impact probability distributions during LLM token generation?"
        ]
    },
    "Python": {
        "Easy": [
            "What is the difference between a list and a tuple in Python?",
            "Explain what a dictionary is and how keys are stored.",
            "What are list comprehensions, and how do they compare to standard loops?"
        ],
        "Medium": [
            "What is the Global Interpreter Lock (GIL), and how does it affect multi-threading in Python?",
            "Explain how memory management and garbage collection work in Python.",
            "What is a decorator in Python, and how do you write a custom one?"
        ],
        "Hard": [
            "Explain the difference between multiprocessing and multithreading in CPU-bound vs I/O-bound tasks in Python.",
            "How do generators and `yield` work under the hood in terms of memory efficiency?",
            "Explain the difference between shallow copy and deep copy using the `copy` module."
        ],
        "Expert": [
            "How do metaclasses work in Python, and how can they customize class creation?",
            "Explain the event loop and coroutine lifecycle execution in `asyncio` compared to OS threads.",
            "Describe the underlying CPython implementation of hash tables and how resizing is triggered."
        ]
    },
    "Java": {
        "Easy": [
            "What is the difference between JDK, JRE, and JVM?",
            "Explain the difference between `==` and `.equals()` in Java.",
            "What is the purpose of the `garbage collector` in Java?"
        ],
        "Medium": [
            "Explain the difference between a Checked Exception and an Unchecked Exception.",
            "What is the Java Memory Model, and what does the `volatile` keyword guarantee?",
            "Compare `ArrayList` and `LinkedList` in terms of lookup and insertion performance."
        ],
        "Hard": [
            "How does the JVM garbage collection work (Generational GC, G1 GC, ZGC)?",
            "What is the purpose of `CompletableFuture`, and how does it enable asynchronous programming?",
            "Explain how the `HashMap` resizing and treeification work under collision threshold in Java 8."
        ],
        "Expert": [
            "Design a high-performance thread pool using `ThreadPoolExecutor` and custom task rejection handlers.",
            "Explain JVM bytecode execution, JIT compilation, and ClassLoader hierarchy delegation overrides.",
            "How do strong, weak, soft, and phantom references impact Java garbage collection sweeps?"
        ]
    },
    "Aptitude": {
        "Easy": [
            "If a train travels at 60 km/h, how long does it take to cover 150 km?",
            "Solve: If 5 men can complete a job in 12 days, how many days will 10 men take?",
            "A shopkeeper marks up an item by 20% and then offers a 10% discount. What is the net profit percentage?"
        ],
        "Medium": [
            "A jar contains a mixture of milk and water in the ratio 4:1. If 10 liters of mixture is replaced by water, the ratio becomes 2:3. What was the initial quantity of milk?",
            "A person covers a distance in three equal parts at speeds of 10, 15, and 30 km/h. What is the average speed?",
            "In how many ways can the letters of the word 'LEADER' be arranged?"
        ],
        "Hard": [
            "Two pipes A and B can fill a tank in 20 and 30 minutes respectively. Both pipes are opened, but after 5 minutes, pipe A is closed. How much longer will it take to fill the tank?",
            "A card is drawn from a pack of 52 cards. What is the probability that it is a king or a spade?",
            "Find the compound interest on $10,000 for 2 years at 10% per annum, compounded half-yearly."
        ],
        "Expert": [
            "Three athletes run a circular race of 12 km. Their speeds are 3, 4, and 6 km/h respectively. When will they meet again at the starting point?",
            "Determine the number of trailing zeroes in 100 factorial (100!).",
            "A bag contains 6 red and 4 blue balls. If 3 balls are drawn at random, what is the probability that at least 2 are red?"
        ]
    }
}
