"""
Tests for QAOA implementation.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from qoptisolve.qaoa import QAOA
from qoptisolve.problems import create_sample_portfolio, create_sample_maxcut


class TestQAOA:
    """Test QAOA solver functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.qaoa = QAOA(shots=100)
        self.portfolio_problem = create_sample_portfolio(n_assets=3, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=4, seed=42)
    
    def test_qaoa_initialization(self):
        """Test QAOA initialization."""
        assert self.qaoa.shots == 100
        assert self.qaoa.backend_name == 'qasm_simulator'
    
    def test_portfolio_circuit_creation(self):
        """Test portfolio circuit creation."""
        circuit = self.qaoa.create_portfolio_circuit(self.portfolio_problem, p=2)
        
        assert circuit.num_qubits == 3
        assert circuit.num_clbits == 3
        
        # Check that we have the right number of parameters
        parameters = circuit.parameters
        assert len(parameters) == 4  # 2 gamma + 2 beta for p=2
    
    def test_maxcut_circuit_creation(self):
        """Test Max-Cut circuit creation."""
        circuit = self.qaoa.create_maxcut_circuit(self.maxcut_problem, p=1)
        
        assert circuit.num_qubits == 4
        assert circuit.num_clbits == 4
        
        # Check that we have the right number of parameters
        parameters = circuit.parameters
        assert len(parameters) == 2  # 1 gamma + 1 beta for p=1
    
    def test_circuit_structure(self):
        """Test that circuits have expected structure."""
        circuit = self.qaoa.create_portfolio_circuit(self.portfolio_problem, p=1)
        
        # Should start with Hadamard gates
        first_gate = circuit.data[0][0]
        assert first_gate.name == 'h'
        
        # Should end with measurements
        last_gate = circuit.data[-1][0]
        assert last_gate.name == 'measure'
    
    @patch('qoptisolve.qaoa.execute')
    @patch('qoptisolve.qaoa.SPSA')
    def test_portfolio_solve_mock(self, mock_spsa, mock_execute):
        """Test portfolio solving with mocked backend."""
        # Mock the optimizer
        mock_optimizer = Mock()
        mock_optimizer.minimize.return_value = Mock(
            x=np.array([1.0, 2.0]),
            fun=-0.5,
            nfev=50
        )
        mock_spsa.return_value = mock_optimizer
        
        # Mock the quantum execution
        mock_job = Mock()
        mock_job.result.return_value = Mock(
            get_counts=lambda: {'000': 50, '001': 30, '010': 20}
        )
        mock_execute.return_value = mock_job
        
        # Solve
        result = self.qaoa.solve_portfolio(self.portfolio_problem, p=1, max_iter=50)
        
        assert result['allocation'] is not None
        assert result['final_cost'] == -0.5
        assert result['convergence'] == 50
        assert len(result['optimal_params']) == 2
    
    @patch('qoptisolve.qaoa.execute')
    @patch('qoptisolve.qaoa.SPSA')
    def test_maxcut_solve_mock(self, mock_spsa, mock_execute):
        """Test Max-Cut solving with mocked backend."""
        # Mock the optimizer
        mock_optimizer = Mock()
        mock_optimizer.minimize.return_value = Mock(
            x=np.array([1.0, 2.0]),
            fun=-2.0,
            nfev=75
        )
        mock_spsa.return_value = mock_optimizer
        
        # Mock the quantum execution
        mock_job = Mock()
        mock_job.result.return_value = Mock(
            get_counts=lambda: {'0000': 40, '0001': 35, '0010': 25}
        )
        mock_execute.return_value = mock_job
        
        # Solve
        result = self.qaoa.solve_maxcut(self.maxcut_problem, p=1, max_iter=75)
        
        assert result['partition'] is not None
        assert result['cut_value'] >= 0
        assert result['final_cost'] == 2.0
        assert result['convergence'] == 75
        assert len(result['optimal_params']) == 2
    
    def test_invalid_optimizer(self):
        """Test that invalid optimizer raises error."""
        with pytest.raises(ValueError):
            self.qaoa.solve_portfolio(self.portfolio_problem, optimizer='invalid')
        
        with pytest.raises(ValueError):
            self.qaoa.solve_maxcut(self.maxcut_problem, optimizer='invalid')
    
    def test_circuit_parameter_binding(self):
        """Test that circuit parameters can be bound."""
        circuit = self.qaoa.create_portfolio_circuit(self.portfolio_problem, p=1)
        
        # Should have 2 parameters for p=1
        assert len(circuit.parameters) == 2
        
        # Test parameter binding
        params = [1.0, 2.0]
        bound_circuit = circuit.bind_parameters(params)
        
        # Bound circuit should have no parameters
        assert len(bound_circuit.parameters) == 0


class TestQAOAHamiltonians:
    """Test QAOA Hamiltonian construction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.qaoa = QAOA()
        self.portfolio_problem = create_sample_portfolio(n_assets=2, seed=42)
        self.maxcut_problem = create_sample_maxcut(n_nodes=3, seed=42)
    
    def test_portfolio_cost_hamiltonian(self):
        """Test portfolio cost Hamiltonian construction."""
        from qiskit import QuantumCircuit
        from qiskit.circuit import Parameter
        
        qc = QuantumCircuit(2)
        gamma = Parameter('γ_0')
        
        # This should not raise an error
        self.qaoa._add_portfolio_cost_hamiltonian(qc, self.portfolio_problem, gamma)
        
        # Circuit should have some gates added
        assert len(qc.data) > 0
    
    def test_maxcut_cost_hamiltonian(self):
        """Test Max-Cut cost Hamiltonian construction."""
        from qiskit import QuantumCircuit
        from qiskit.circuit import Parameter
        
        qc = QuantumCircuit(3)
        gamma = Parameter('γ_0')
        
        # This should not raise an error
        self.qaoa._add_maxcut_cost_hamiltonian(qc, self.maxcut_problem, gamma)
        
        # Circuit should have some gates added
        assert len(qc.data) > 0
    
    def test_mixing_hamiltonian(self):
        """Test mixing Hamiltonian construction."""
        from qiskit import QuantumCircuit
        from qiskit.circuit import Parameter
        
        qc = QuantumCircuit(3)
        beta = Parameter('β_0')
        
        # This should not raise an error
        self.qaoa._add_mixing_hamiltonian(qc, beta)
        
        # Should have 3 RX gates (one per qubit)
        rx_gates = [gate for gate in qc.data if gate[0].name == 'rx']
        assert len(rx_gates) == 3
