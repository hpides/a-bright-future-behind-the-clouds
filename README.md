# CIDR 2027

## Setup:
 - Docker
  - Umbra
  - Postgres
  - (DuckDB)
 - BenchBase
  - provides TPC-C, TPC-H, and YCSB

## Status:
 - using Docker
 - we can run all three databases
 - we are in the process of getting BenchBase set up

### Setup Questions:
 - how to evaluate TPC-C?
 - how to evaluate TPC-H?
  - which scale factors for Raspberry Pi vs. AMD Zen5?
  - test 1, 2, 4, 8, 16, 32, 64, 128

### General Open Questions:
 - SemBench:
   - can we do Lora stuff?
   - exolab interence?
   - compare DGX vs. "our" DES MacBook cluster?
   - **is this collective GPU stuff relevant at all?**
