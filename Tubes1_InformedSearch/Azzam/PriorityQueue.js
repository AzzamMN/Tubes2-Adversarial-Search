/**
 * Implementasi Bare-Metal: Min-Priority Queue berbasis Binary Heap.
 * Dilarang menggunakan method sort() bawaan array karena kompleksitasnya O(N log N) per iterasi.
 * Struktur ini menjamin O(log N) untuk operasi Enqueue dan Dequeue.
 */
class PriorityQueue {
    constructor() {
        this.heap = [];
    }

    enqueue(element, priority) {
        const node = { element, priority };
        this.heap.push(node);
        this._bubbleUp(this.heap.length - 1);
    }

    dequeue() {
        if (this.isEmpty()) return null;
        const min = this.heap[0];
        const end = this.heap.pop();
        if (this.heap.length > 0) {
            this.heap[0] = end;
            this._sinkDown(0);
        }
        return min;
    }

    isEmpty() {
        return this.heap.length === 0;
    }

    _bubbleUp(index) {
        const node = this.heap[index];
        while (index > 0) {
            const parentIndex = Math.floor((index - 1) / 2);
            const parent = this.heap[parentIndex];
            if (node.priority >= parent.priority) break;
            this.heap[index] = parent;
            index = parentIndex;
        }
        this.heap[index] = node;
    }

    _sinkDown(index) {
        const length = this.heap.length;
        const node = this.heap[index];
        while (true) {
            let leftChildIndex = 2 * index + 1;
            let rightChildIndex = 2 * index + 2;
            let leftChild, rightChild;
            let swap = null;

            if (leftChildIndex < length) {
                leftChild = this.heap[leftChildIndex];
                if (leftChild.priority < node.priority) {
                    swap = leftChildIndex;
                }
            }
            if (rightChildIndex < length) {
                rightChild = this.heap[rightChildIndex];
                if (
                    (swap === null && rightChild.priority < node.priority) ||
                    (swap !== null && rightChild.priority < leftChild.priority)
                ) {
                    swap = rightChildIndex;
                }
            }
            if (swap === null) break;
            this.heap[index] = this.heap[swap];
            index = swap;
        }
        this.heap[index] = node;
    }
}
