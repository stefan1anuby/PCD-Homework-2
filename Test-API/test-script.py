import socketio
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

WS_URL = 'http://35.244.240.185:5000'  # Server URL (adjust as needed)
NUM_CLIENTS = 100                      # Number of clients
MESSAGES_PER_CLIENT = 10               # Messages per client
MAX_CONCURRENT = 10                    # Max concurrent connections

metrics = {
    'total_messages_sent': 0,
    'total_connection_errors': 0,
    'client_metrics': []
}

async def simulate_client(client_id):
    sio = socketio.Client()
    start_time = time.time()
    messages_sent = 0
    callback_called = False
    
    try:
        @sio.event
        def connect():
            nonlocal messages_sent, callback_called
            print(f'[Client {client_id}] Connected')
            
            # Send MESSAGES_PER_CLIENT messages
            for i in range(MESSAGES_PER_CLIENT):
                message = {
                    'author': f'User{client_id}',
                    'message': f'Message {i + 1} from client {client_id}',
                    'label': 'LabelFalse'
                }
                sio.emit('chat message', (message['author'], message['message'], message['label']))
                print(f'[Client {client_id}] Sent: {message["message"]}')
                messages_sent += 1
            
            @sio.event
            def disconnect():
                nonlocal callback_called
                if not callback_called:
                    time_taken = (time.time() - start_time) * 1000  # in ms
                    print(f'[Client {client_id}] Disconnected')
                    
                    metrics['client_metrics'].append({
                        'client_id': client_id,
                        'messages_sent': messages_sent,
                        'time_taken': time_taken
                    })
                    
                    metrics['total_messages_sent'] += messages_sent
                    callback_called = True
                    sio.disconnect()
        
        sio.connect(WS_URL)
        
        # Wait for messages to be sent and disconnect
        while not callback_called and sio.connected:
            await asyncio.sleep(0.1)
            
    except Exception as e:
        if not callback_called:
            print(f'[Client {client_id}] Connection Error: {str(e)}')
            metrics['total_connection_errors'] += 1
            callback_called = True

async def run_load_test():
    # Using ThreadPoolExecutor to run clients concurrently
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, asyncio.run, simulate_client(client_id))
            for client_id in range(1, NUM_CLIENTS + 1)
        ]
        await asyncio.gather(*tasks)
    
    print('All clients finished.')
    print('Metrics:', metrics)
    generate_metrics_visualization(metrics)

def generate_metrics_visualization(metrics):
    # Extract meaningful data
    times = [m['time_taken']/1000 for m in metrics['client_metrics']]  # Convert to seconds
    completion_times = np.cumsum(times)  # When each client finished
    total_messages = metrics['total_messages_sent']
    error_count = metrics['total_connection_errors']
    
    # Calculate core metrics
    avg_time = np.mean(times)
    max_time = max(times)
    min_time = min(times)
    overall_throughput = total_messages/max(times) if max(times) > 0 else 0  # Renamed this
    
    # Create only meaningful visualizations
    plt.figure(figsize=(12, 8))
    
    # 1. Response Time Distribution
    plt.subplot(2, 1, 1)
    plt.hist(times, bins=20, color='#1f77b4', edgecolor='black')
    plt.title('Response Time Distribution', pad=10, fontweight='bold')
    plt.xlabel('Time to complete (seconds)')
    plt.ylabel('Number of Clients')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.axvline(avg_time, color='red', linestyle='--', label=f'Average: {avg_time:.2f}s')
    plt.legend()
    
    # 2. Load Completion Timeline
    plt.subplot(2, 1, 2)
    plt.plot(completion_times, range(1, len(completion_times)+1), 
             'b-', linewidth=2, label='Clients Completed')
    
    # Calculate throughput trend (for the plot only)
    window_size = max(1, len(completion_times)//10)
    throughput = window_size / np.diff(completion_times, prepend=0)[window_size-1:]
    smooth_throughput = np.convolve(throughput, np.ones(window_size)/window_size, mode='valid')
    
    ax2 = plt.gca().twinx()
    ax2.plot(completion_times[window_size-1:window_size+len(smooth_throughput)-1], 
             smooth_throughput, 
             'r--', label=f'Throughput (last {window_size} clients)')
    
    plt.title('Load Completion Timeline', fontweight='bold', pad=10)
    plt.xlabel('Test Time (seconds)')
    plt.ylabel('Clients Completed', color='b')
    ax2.set_ylabel('Messages/sec', color='r')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    # 3. Text Summary - using the overall_throughput instead of the array
    plt.figtext(0.5, 0.05,
                f"STRESS TEST RESULTS | "
                f"Clients: {len(times)} | "
                f"Messages: {total_messages} | "
                f"Avg Time: {avg_time:.2f}s | "
                f"Throughput: {overall_throughput:.1f} msg/s | "  # Fixed here
                f"Errors: {error_count}",
                ha="center", fontsize=12, bbox=dict(facecolor='#f0f0f0', alpha=0.5))
    
    plt.tight_layout()
    filename = f"loadtest_results_{int(time.time())}.png"
    plt.savefig(filename, dpi=120, bbox_inches='tight')
    print(f"\n✅ Saved meaningful metrics to {filename}")
    plt.close()

if __name__ == '__main__':
    asyncio.run(run_load_test())