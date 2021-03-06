import h5py
import os

import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
import matplotlib.pyplot as plt
import numpy as np
import scipy.special
import scipy.optimize as opt

plt.rcParams.update({
    "text.usetex": True,
    "text.latex.preamble": '\\usepackage{siunitx}'
})

magnetization_name = "magnetization"
field_squared_name = "field_squared"
magnetization_squared_name = "magnetization_squared"
energy_name = "energy"
energy_squared_name = "energy_squared"


def fit_function(x, a, z):
    return a * x ** z


def magnetization_exact(beta):
    if beta < 0.440686793509772:
        return 0
    else:
        return (1. - 1. / np.sinh(2 * beta) ** 4) ** (1 / 8)


def ene_exact(J):  # exact internal energy in thermodynamic limit (for h=0)\n",
    J2 = 2 * J
    k = 4 * np.sinh(J2) ** 2 / np.cosh(J2) ** 4
    eK = scipy.special.ellipk(k)
    answer = 1 + (2 / np.pi) * (2 * np.tanh(J2) ** 2 - 1) * eK
    return -J * np.cosh(J2) * answer / np.sinh(J2)


def specific_heat_exact(beta):  # exact cpecific_heat in thermodynamic limit (for h=0)\n",
    B2 = 2 * beta
    k = 4 * np.sinh(B2) ** 2 / np.cosh(B2) ** 4
    Kk = scipy.special.ellipk(k)
    Ek = scipy.special.ellipe(k)
    kp = 2 * (np.tanh(B2) ** 2) - 1
    answer = 2 * Kk - 2 * Ek - (1 - kp) * ((np.pi / 2) + kp * Kk)
    return ((2 * beta ** 2 / np.pi) / (np.tanh(B2) ** 2)) * answer


def append_observable(name, measurements_group_, observable_list, observable_error_list):
    observable_group = measurements_group_.get(name)
    temp = -42
    if "bootstrap_mean_10000_100000" in observable_group.attrs:
        temp = observable_group.attrs["bootstrap_mean_10000_100000"]
        print("hi")
    else:
        temp = observable_group.attrs["bootstrap_mean"]
    if np.isinf(temp) or temp > 1e200:
        observable_list.append(-42)
    else:
        observable_list.append(temp)

    if "bootstrap_variance_10000_100000" in observable_group.attrs:
        temp = observable_group.attrs["bootstrap_variance_10000_100000"]
        print("hey")
    else:
        temp = observable_group.attrs["bootstrap_variance"]
    if np.isinf(temp) or temp > 1e200 or np.isnan(temp):
        observable_error_list.append(42)
    else:
        observable_error_list.append(np.sqrt(temp))


def make_auto_correlation_plot_to_ax(name, measurements_group_, ax_, suffix="", label=""):
    observable_group = measurements_group_.get(name)
    observable_auto_correlation_dataset = observable_group.get("auto_correlation" + suffix)
    observable_auto_correlation = np.zeros(observable_auto_correlation_dataset.size)
    observable_auto_correlation_dataset.read_direct(observable_auto_correlation,
                                                    np.s_[0:observable_auto_correlation_dataset.size],
                                                    np.s_[0:observable_auto_correlation_dataset.size])

    ax_.plot(np.arange(observable_auto_correlation.size), observable_auto_correlation, label=label)


def make_auto_correlation_plot(name, measurements_group_, suffix=""):
    fig_, ax_ = plt.subplots()
    fig_: plt.Figure
    ax_: plt.Axes
    make_auto_correlation_plot_to_ax(name, measurements_group_, ax_, suffix)
    ax_.set_xlabel(r"t")
    ax_.set_ylabel(r"$\bar{\Gamma}_{m}$")
    # ax_.set_yscale("log")
    ax_.set_xlim(-1, 100)
    fig_.set_tight_layout(True)
    return fig_, ax_


def make_observable_plot(name, inverse_betas, observable_list, observable_error_list):
    fig_, ax_ = plt.subplots()
    fig_: plt.Figure
    ax_: plt.Axes
    ax_.errorbar(inverse_betas, observable_list, observable_error_list,
                 color='green', fmt='.', markersize='10', ecolor='red', capsize=4, label="Measurements")

    ax_.set_xlabel(r"1/$\beta$")
    ax_.set_ylabel(name)
    fig_.set_tight_layout(True)
    return fig_, ax_


def base_plot(sub_folder_name="std_hmc/"):
    betas = []
    inverse_betas = []
    magnetizations = []
    magnetizations_errors = []
    magnetizations_squared = []
    magnetizations_squared_errors = []
    energies = []
    energies_errors = []
    energies_squared = []
    energies_squared_errors = []

    for file in os.listdir(sub_folder_name):
        if file.startswith("out_"):
            file = sub_folder_name + file
            print(file)
            f = h5py.File(file, 'r')

            level0_group = f.get("level0")

            measurements_group = level0_group.get("measurements")

            betas.append(level0_group.attrs["beta"])
            inverse_betas.append(1. / betas[-1])

            if energy_name in measurements_group:
                append_observable(energy_name, measurements_group, energies, energies_errors)
                fig, ax = make_auto_correlation_plot(energy_name, measurements_group)
                fig.savefig(sub_folder_name + energy_name + f"_auto_correlation_{inverse_betas[-1]}.png")
                plt.close(fig)

            if magnetization_name in measurements_group:
                append_observable(magnetization_name, measurements_group, magnetizations, magnetizations_errors)
                # fig, ax = make_auto_correlation_plot(magnetization_name, measurements_group)
                # fig.savefig(sub_folder_name + magnetization_name + "_auto_correlation.png")
                # plt.close(fig)

            if energy_squared_name in measurements_group:
                append_observable(energy_squared_name, measurements_group, energies_squared, energies_squared_errors)
                # fig, ax = make_auto_correlation_plot(energy_squared_name, measurements_group)
                # fig.savefig(sub_folder_name + energy_squared_name + "_auto_correlation.png")
                # plt.close(fig)

            if magnetization_squared_name in measurements_group:
                append_observable(magnetization_squared_name, measurements_group, magnetizations_squared,
                                  magnetizations_squared_errors)
                # fig, ax = make_auto_correlation_plot(magnetization_squared_name, measurements_group)
                # fig.savefig(sub_folder_name + magnetization_squared_name + "_auto_correlation.png")
                # plt.close(fig)

    # magnetizations
    beta_lin = np.linspace(0.25, 3, 1000)
    if len(magnetizations) > 0:
        m_exact = np.array([magnetization_exact(temp) for temp in beta_lin])
        fig, ax = make_observable_plot(magnetization_name, inverse_betas, magnetizations, magnetizations_errors)
        ax.set_ylabel("$<m>$")
        ax.plot(1. / beta_lin, m_exact, label="Thermodynamic limit")
        ax.plot(1. / beta_lin, -m_exact, label="-Thermodynamic limit")
        ax.legend()
        fig.savefig(sub_folder_name + magnetization_name + ".png", dpi=1000)
        plt.close(fig)

    # magnetizations_squared
    if len(magnetizations_squared) > 0:
        m_squared_exact = m_exact ** 2  # todo
        fig, ax = make_observable_plot(magnetization_squared_name, inverse_betas, magnetizations_squared,
                                       magnetizations_squared_errors)
        ax.set_ylabel("$<m^2>$")
        ax.plot(1. / beta_lin, m_squared_exact, label="Thermodynamic limit")
        ax.legend()
        fig.savefig(sub_folder_name + magnetization_squared_name + ".png", dpi=1000)
        plt.close(fig)

    # energies
    if len(energies) > 0:
        e_exact = np.array([ene_exact(temp) / temp for temp in beta_lin])
        fig, ax = make_observable_plot(energy_name, inverse_betas, energies, energies_errors)
        # ax.set_ylim(0, 1.2)
        ax.set_ylabel("$<e>$")
        ax.plot(1. / beta_lin, e_exact, label="Thermodynamic limit")
        ax.legend()
        fig.savefig(sub_folder_name + energy_name + ".png", dpi=1000)
        plt.close(fig)

    # energies_squared
    if len(energies_squared) > 0:
        energies_squared = np.array(energies_squared)
        energies = np.array(energies)
        c_exact = np.array([specific_heat_exact(temp) / temp for temp in beta_lin])
        fig, ax = make_observable_plot(energy_squared_name, inverse_betas, energies_squared - energies ** 2,
                                       energies_squared_errors)
        ax.set_ylabel("$<C>$")
        ax.plot(1. / beta_lin, c_exact, label="Thermodynamic limit")
        ax.legend()
        fig.savefig(sub_folder_name + energy_squared_name + ".png", dpi=1000)
        plt.close(fig)


def info_plot(sub_folder_name, observable_name=magnetization_name):
    int_auto_correlation_time = []
    int_auto_correlation_time_bias = []
    int_auto_correlation_time_stat_error = []
    gamma = []
    system_size = []
    tick_time = []
    interpolation_type = []
    nu_pre_level0 = []
    nu_post_level0 = []
    nu_pre_level1 = []
    nu_post_level1 = []
    bootstrap_variance = []
    bootstrap_mean = []
    file_list = []
    fig_correl, ax_correl = plt.subplots()
    fig_correl: plt.Figure
    ax_correl: plt.Axes
    for file in os.listdir(sub_folder_name):
        if file.startswith("out_") and file.endswith(".h5"):
            file_list.append(sub_folder_name + file)

    for file in file_list:
        print(file)
        f = h5py.File(file, 'r')

        level0_group = f.get("level0")

        measurements_group = level0_group.get("measurements")
        if observable_name in measurements_group:
            observable_group = measurements_group.get(observable_name)
            last_sufix = ""
            temp_int_auto_correlation_time = []
            temp_int_auto_correlation_time_stat_error = []
            temp_x = []
            for i in range(1000, 100001, 1000):
                sufix = f"_{i}_{100000}"
                if "int_auto_correlation_time" + sufix in observable_group.attrs:
                    temp_int_auto_correlation_time.append(observable_group.attrs["int_auto_correlation_time" + sufix])
                    temp_int_auto_correlation_time_stat_error.append(
                        observable_group.attrs["int_auto_correlation_time_stat_error" + sufix])
                    temp_x.append(100000 - i)
                    if len(last_sufix) == 0:
                        last_sufix = sufix
            fig_, ax_ = plt.subplots()
            fig_: plt.Figure
            ax_: plt.Axes
            ax_.errorbar(temp_x, temp_int_auto_correlation_time, temp_int_auto_correlation_time_stat_error, fmt='o')
            title = f"Grid side length =" + file.split('/')[1].split('_')[1][2:]

            int_auto_correlation_time.append(observable_group.attrs["int_auto_correlation_time" + last_sufix])
            int_auto_correlation_time_bias.append(observable_group.attrs["int_auto_correlation_time_bias" + last_sufix])
            int_auto_correlation_time_stat_error.append(
                observable_group.attrs["int_auto_correlation_time_stat_error" + last_sufix])
            gamma.append(level0_group.attrs["gamma"])
            system_size.append(len(level0_group.get("h")))

            tick_time.append(level0_group.attrs["tick_time"])
            interpolation_type.append(level0_group.attrs["inter_type"])
            nu_pre_level0.append(level0_group.attrs["nu_pre"])
            nu_post_level0.append(level0_group.attrs["nu_post"])
            label = "abc"
            if "level1" in f:
                if gamma[-1]>1:
                    label = "MLHMC  W-cycle"
                else:
                    label = "MLHMC V-cycle"
                title = "MLHMC " + title
                level1_group = f.get("level1")
                nu_pre_level1.append(level1_group.attrs["nu_pre"])
                nu_post_level1.append(level1_group.attrs["nu_post"])
            else:
                label = "HMC"
                title = "HMC " + title
                nu_pre_level1.append(-1)
                nu_post_level1.append(-1)

            if system_size[-1] == 32 * 32:
                make_auto_correlation_plot_to_ax(observable_name, measurements_group, ax_correl, last_sufix, label)
                ax_correl.set_xlabel(r"t")
                ax_correl.set_ylabel(r"$\bar{\Gamma}_{m}$")
                # ax_.set_yscale("log")
                ax_correl.set_xlim(-1, 6000)
                ax_correl.set_ylim(0, 1.05)
                fig_correl.set_tight_layout(True)

            ax_.set_title(title)
            ax_.set_xlabel("$N_{ensemble}$")
            ax_.set_ylabel(r"$\tau$")
            ax_.set_yscale("log")
            fig_.set_tight_layout(True)
            # fig_.savefig(file.split('.')[0] + observable_name + "test")
            plt.close(fig_)

    ax_correl.legend()
    fig_correl.savefig(sub_folder_name + observable_name + f"_auto_correlation_{42}.png", dpi=1000)
    plt.close(fig_correl)
    int_auto_correlation_time = np.array(int_auto_correlation_time)
    int_auto_correlation_time_bias = np.array(int_auto_correlation_time_bias)
    int_auto_correlation_time_stat_error = np.array(int_auto_correlation_time_stat_error)
    gamma = np.array(gamma)
    system_size = np.array(system_size)
    tick_time = np.array(tick_time)
    interpolation_type = np.array(interpolation_type)
    nu_pre_level0 = np.array(nu_pre_level0)
    nu_post_level0 = np.array(nu_post_level0)
    nu_pre_level1 = np.array(nu_pre_level1)
    nu_post_level1 = np.array(nu_post_level1)

    fig_, (ax1_, ax2_, ax3_) = plt.subplots(3, 1, figsize=(12, 9))
    fig_, ax1_ = plt.subplots(1, 1)
    fig_: plt.Figure
    ax1_: plt.Axes
    ax2_: plt.Axes
    ax3_: plt.Axes
    base_bootstrap_variance = []
    base_bootstrap_mean = []
    base_tick_time = np.zeros(1)
    base_int_auto_correlation_time = 42
    ls = [0, 0]
    labels = ["HMC", "Multilevel"]
    x_wo_bias_correction_hmc = []
    y_wo_bias_correction_hmc = []
    yerr_wo_bias_correction_hmc = []
    x_wo_bias_correction_multi_hmc = []
    y_wo_bias_correction_multi_hmc = []
    yerr_wo_bias_correction_multi_hmc = []
    y_w_bias_correction_hmc = []
    y_w_bias_correction_multi_hmc = []
    hmc_first = True
    mlhmc_first = True
    for i, nu_pre in enumerate(nu_pre_level1):
        if nu_pre == -1:
            if hmc_first:
                ls[0] = ax1_.errorbar(np.sqrt(system_size[i]), int_auto_correlation_time[i],
                                      int_auto_correlation_time_stat_error[i],
                                      fmt='.', mfc='red', mec='red', ecolor='red', label="HMC", zorder=2)
                hmc_first = False
            else:
                ls[0] = ax1_.errorbar(np.sqrt(system_size[i]), int_auto_correlation_time[i],
                                      int_auto_correlation_time_stat_error[i],
                                      fmt='.', mfc='red', mec='red', ecolor='red', zorder=2)
            ax2_.errorbar(np.sqrt(system_size[i]), int_auto_correlation_time[i] + int_auto_correlation_time_bias[i],
                          int_auto_correlation_time_stat_error[i],
                          fmt='.', mfc='red', mec='red', ecolor='red')
            if system_size[i] < 33 * 33:
                x_wo_bias_correction_hmc.append(np.sqrt(system_size[i]))
                y_wo_bias_correction_hmc.append(int_auto_correlation_time[i])
                y_w_bias_correction_hmc.append(int_auto_correlation_time[i] + int_auto_correlation_time_bias[i])
                yerr_wo_bias_correction_hmc.append(int_auto_correlation_time_stat_error[i])
                if system_size[i] < 5 * 5:
                    x_wo_bias_correction_multi_hmc.append(np.sqrt(system_size[i]))
                    y_wo_bias_correction_multi_hmc.append(int_auto_correlation_time[i])
                    y_w_bias_correction_multi_hmc.append(
                        int_auto_correlation_time[i] + int_auto_correlation_time_bias[i])
                    yerr_wo_bias_correction_multi_hmc.append(int_auto_correlation_time_stat_error[i])
            ax3_.scatter(np.sqrt(system_size[i]), int_auto_correlation_time_bias[i], c='red')
        else:
            if mlhmc_first:
                ls[1] = ax1_.errorbar(np.sqrt(system_size[i]), int_auto_correlation_time[i],
                                      int_auto_correlation_time_stat_error[i],
                                      fmt='.', mfc='green', mec='green', ecolor='green', label="MLHMC", zorder=2)
                mlhmc_first = False
            else:
                ls[1] = ax1_.errorbar(np.sqrt(system_size[i]), int_auto_correlation_time[i],
                                      int_auto_correlation_time_stat_error[i],
                                      fmt='.', mfc='green', mec='green', ecolor='green', zorder=2)
            ax2_.errorbar(np.sqrt(system_size[i]), int_auto_correlation_time[i] + int_auto_correlation_time_bias[i],
                          int_auto_correlation_time_stat_error[i],
                          fmt='.', mfc='green', mec='green', ecolor='green')
            if system_size[i] < 33 * 33:
                x_wo_bias_correction_multi_hmc.append(np.sqrt(system_size[i]))
                y_wo_bias_correction_multi_hmc.append(int_auto_correlation_time[i])
                y_w_bias_correction_multi_hmc.append(int_auto_correlation_time[i] + int_auto_correlation_time_bias[i])
                yerr_wo_bias_correction_multi_hmc.append(int_auto_correlation_time_stat_error[i])
            ax3_.scatter(np.sqrt(system_size[i]), int_auto_correlation_time_bias[i], c='green')

    popt, pcov = opt.curve_fit(fit_function, x_wo_bias_correction_hmc, y_wo_bias_correction_hmc,
                               sigma=yerr_wo_bias_correction_hmc)
    f = open(sub_folder_name + observable_name + "_output.txt", "w")
    x_wo_bias_correction_hmc = np.array(x_wo_bias_correction_hmc)
    y_wo_bias_correction_hmc = np.array(y_wo_bias_correction_hmc)
    yerr_wo_bias_correction_hmc = np.array(yerr_wo_bias_correction_hmc)
    chi2 = (((y_wo_bias_correction_hmc - fit_function(x_wo_bias_correction_hmc,
                                                      *popt)) / yerr_wo_bias_correction_hmc) ** 2).sum() / (
                   len(x_wo_bias_correction_hmc) - len(popt))
    print("HMC", observable_name, "a =", popt[0], "+-", np.sqrt(pcov[0, 0]), "z =", popt[1], "+-", np.sqrt(pcov[1, 1]),
          "chi2 =", chi2,
          file=f)
    print("HMC", pcov)
    x_fit = np.linspace(3.8, 40)
    y_fit = fit_function(x_fit, *popt)
    ax1_.plot(x_fit, y_fit, label="HMC fit", zorder=1)

    popt, pcov = opt.curve_fit(fit_function, x_wo_bias_correction_multi_hmc, y_wo_bias_correction_multi_hmc,
                               sigma=yerr_wo_bias_correction_multi_hmc)
    x_wo_bias_correction_multi_hmc = np.array(x_wo_bias_correction_multi_hmc)
    y_wo_bias_correction_multi_hmc = np.array(y_wo_bias_correction_multi_hmc)
    yerr_wo_bias_correction_multi_hmc = np.array(yerr_wo_bias_correction_multi_hmc)
    chi2 = (((y_wo_bias_correction_multi_hmc - fit_function(x_wo_bias_correction_multi_hmc,
                                                            *popt)) / yerr_wo_bias_correction_multi_hmc) ** 2).sum() / (
                   len(x_wo_bias_correction_multi_hmc) - len(popt))
    print("MLHMC", observable_name, "a =", popt[0], "+-", np.sqrt(pcov[0, 0]), "z =", popt[1], "+-",
          np.sqrt(pcov[1, 1]), "chi2 =", chi2, file=f)
    print("MLHMC", pcov)
    f.close()
    y_fit = fit_function(x_fit, *popt)
    ax1_.plot(x_fit, y_fit, label="MLHMC fit", zorder=1)

    ax1_.legend(loc="upper left")

    popt, pcov = opt.curve_fit(fit_function, x_wo_bias_correction_hmc, y_w_bias_correction_hmc,
                               sigma=yerr_wo_bias_correction_hmc)
    # print("hmc w_bias_correction", observable_name, popt, np.sqrt(pcov[0, 0]), np.sqrt(pcov[1, 1]))
    y_fit = fit_function(x_fit, *popt)
    ax2_.plot(x_fit, y_fit, label="HMC")

    popt, pcov = opt.curve_fit(fit_function, x_wo_bias_correction_multi_hmc, y_w_bias_correction_multi_hmc,
                               sigma=yerr_wo_bias_correction_multi_hmc)
    # print("Multilevel w_bias_correction", observable_name, popt, np.sqrt(pcov[0, 0]), np.sqrt(pcov[1, 1]))
    y_fit = fit_function(x_fit, *popt)
    ax2_.plot(x_fit, y_fit, label="Multilevel")

    ax2_.legend(loc="upper left")

    # ax1_.set_title("Without bias correction")
    ax2_.set_title("With bias correction")
    # ax1_.legend(ls, labels, loc="upper right")

    # fig_.subplots_adjust(right=0.85)

    ax1_.set_xlabel(r"$l$")
    ax1_.set_ylabel(r"$\bar{\tau}_{\text{int},m}$")
    ax1_.set_xscale('log')
    ax1_.set_yscale('log')

    ax2_.set_xlabel(r"$N$")
    ax2_.set_ylabel(r"$\tau$")
    ax2_.set_xscale('log')
    ax2_.set_yscale('log')

    ax3_.set_xlabel(r"$N$")
    ax3_.set_ylabel("Bias")
    ax3_.set_xscale('log')
    # ax3_.set_yscale('log')

    fig_.set_tight_layout(True)

    fig_.savefig(sub_folder_name + observable_name + sub_folder_name[:-1] + ".png", dpi=1000)
    fig_.clear()


def check_thermalisation(sub_folder_name, observable_name=field_squared_name):
    observable_values = []
    file_list = []
    for file in os.listdir(sub_folder_name):
        if file.startswith("out_"):
            file_list.append(sub_folder_name + file)

    for file in file_list:
        print(file)
        f = h5py.File(file, 'r')

        level0_group = f.get("level0")

        measurements_group = level0_group.get("measurements")
        if observable_name in measurements_group:
            observable_group = measurements_group.get(observable_name)
            observable_values.append(observable_group.get("data"))
        else:
            observable_values.append([])

    for i, observable_value_list in enumerate(observable_values):
        fig_, ax1_ = plt.subplots(1, 1, figsize=(12, 9))
        fig_: plt.Figure
        ax1_: plt.Axes
        ax1_.scatter(np.arange(len(observable_value_list)), observable_value_list, label=file_list[i])

        ax1_.set_title("Without bias correction")
        fig_.legend(loc="upper right")

        ax1_.set_xlabel(r"$N$")
        ax1_.set_ylabel(r"$\tau$")
        # ax1_.set_xscale('log')
        # ax1_.set_yscale('log')

        fig_.savefig(sub_folder_name + observable_name + sub_folder_name[:-1] +
                     file_list[i].split("/")[1].split(".")[0] + ".png", dpi=1000)
        fig_.clear()


def crit_int_auto_correlation_plot_multiple_levels(sub_folder_name, observable_name=magnetization_name):
    int_auto_correlation_time = []
    int_auto_correlation_time_bias = []
    int_auto_correlation_time_stat_error = []
    gamma = []
    tick_time = []
    interpolation_type = []
    nu_pre_level0 = []
    nu_post_level0 = []
    nu_pre_level_x = []
    nu_post_level_x = []
    file_list = []
    for file in os.listdir(sub_folder_name):
        if file.startswith("out_"):
            file_list.append(sub_folder_name + file)

    for file in file_list:
        print(file)
        f = h5py.File(file, 'r')

        level0_group = f.get("level0")

        measurements_group = level0_group.get("measurements")
        if observable_name in measurements_group:
            observable_group = measurements_group.get(observable_name)
            int_auto_correlation_time.append(observable_group.attrs["int_auto_correlation_time"])
            int_auto_correlation_time_bias.append(observable_group.attrs["int_auto_correlation_time_bias"])
            int_auto_correlation_time_stat_error.append(
                observable_group.attrs["int_auto_correlation_time_stat_error"])
            gamma.append(level0_group.attrs["gamma"])
            tick_time.append(level0_group.attrs["tick_time"])
            interpolation_type.append(level0_group.attrs["inter_type"])
            nu_pre_level0.append(level0_group.attrs["nu_pre"])
            nu_post_level0.append(level0_group.attrs["nu_post"])
            temp_pre = []
            temp_post = []
            for i in range(1, 10):
                if f"level{i}" in f:
                    level_x_group = f.get(f"level{i}")
                    temp_pre.append(level_x_group.attrs["nu_pre"])
                    temp_post.append(level_x_group.attrs["nu_post"])
                else:
                    temp_pre.append(-1)
                    temp_post.append(-1)
            nu_pre_level_x.append(temp_pre)
            nu_post_level_x.append(temp_post)

    int_auto_correlation_time = np.array(int_auto_correlation_time)
    int_auto_correlation_time_bias = np.array(int_auto_correlation_time_bias)
    int_auto_correlation_time_stat_error = np.array(int_auto_correlation_time_stat_error)
    gamma = np.array(gamma)
    tick_time = np.array(tick_time)
    interpolation_type = np.array(interpolation_type)
    nu_pre_level0 = np.array(nu_pre_level0)
    nu_post_level0 = np.array(nu_post_level0)
    fig_, (ax1_, ax2_, ax3_) = plt.subplots(3, 1, sharex="all", sharey="row", figsize=(12, 5))
    fig_: plt.Figure
    ax1_: plt.Axes
    ax2_: plt.Axes
    ax3_: plt.Axes
    j = 0
    fig_.subplots_adjust(hspace=0, wspace=0)
    base_index = -1
    for i, nu_pre in enumerate(nu_pre_level_x):
        if nu_pre[0] == -1:
            base_index = i
            break
    base_int_auto_correlation_time = int_auto_correlation_time[base_index]
    base_tick_time = tick_time[base_index]
    ls = []
    labels = []

    ls.append(ax1_.hlines(base_int_auto_correlation_time, 0, 10, colors=list(mcolors.TABLEAU_COLORS.values())[-1]))
    labels.append("HMC")
    ax2_.hlines(base_tick_time, 0, 10, colors=list(mcolors.TABLEAU_COLORS.values())[-1])
    ax3_.hlines(base_int_auto_correlation_time * base_tick_time, 0, 10,
                colors=list(mcolors.TABLEAU_COLORS.values())[-1])

    x_plot = []
    y1_plot = []
    y1_error = []
    y2_plot = []
    for i, nu_pre in enumerate(nu_pre_level_x):
        length = -1
        for j in range(10):
            if nu_pre[j] == -1:
                length = j + 1  # +1 because of level 0
                break
        if length > 1:
            x_plot.append(length)
            y1_plot.append(int_auto_correlation_time[i])
            y1_error.append(int_auto_correlation_time_stat_error[i] + int_auto_correlation_time_bias[i])
            y2_plot.append(tick_time[i])

    x_plot = np.array(x_plot)
    y1_plot = np.array(y1_plot)
    y1_error = np.array(y1_error)
    y2_plot = np.array(y2_plot)

    ls.append(ax1_.errorbar(x_plot, y1_plot, y1_error, marker='.', ls='',
                            c=list(mcolors.TABLEAU_COLORS.values())[j]))
    labels.append(f"nu pre=1")

    ax2_.plot(x_plot, y2_plot, marker='.', ls='', c=list(mcolors.TABLEAU_COLORS.values())[j])

    ax3_.errorbar(x_plot, y1_plot * y2_plot, y1_error * y2_plot, marker='.', ls='',
                  c=list(mcolors.TABLEAU_COLORS.values())[j])

    fig_.legend(ls, labels, loc="upper right")
    fig_.subplots_adjust(right=0.85)
    ax3_.set_xlabel(r"# levels")
    ax1_.set_ylabel(r"$\tau$")
    # ax1_.set_xscale('log')
    # ax1_.set_yscale('log')
    ax2_.set_ylabel(r"t")
    # ax2_.set_xscale('log')
    # ax2_.set_yscale('log')
    ax3_.set_ylabel(r"$t*\tau$")
    # ax3_.set_xscale('log')
    # ax3_.set_yscale('log')
    fig_.savefig(sub_folder_name + observable_name + sub_folder_name[:-1] + ".png", dpi=1000)
    fig_.clear()


def crit_int_auto_correlation_plot(sub_folder_name, observable_name=magnetization_name):
    int_auto_correlation_time = []
    int_auto_correlation_time_bias = []
    int_auto_correlation_time_stat_error = []
    gamma = []
    tick_time = []
    interpolation_type = []
    nu_pre_level0 = []
    nu_post_level0 = []
    nu_pre_level1 = []
    nu_post_level1 = []
    for file in os.listdir(sub_folder_name):
        if file.startswith("out_"):
            file = sub_folder_name + file
            print(file)
            f = h5py.File(file, 'r')

            level0_group = f.get("level0")

            measurements_group = level0_group.get("measurements")
            if observable_name in measurements_group:
                observable_group = measurements_group.get(observable_name)
                int_auto_correlation_time.append(observable_group.attrs["int_auto_correlation_time"])
                int_auto_correlation_time_bias.append(observable_group.attrs["int_auto_correlation_time_bias"])
                int_auto_correlation_time_stat_error.append(
                    observable_group.attrs["int_auto_correlation_time_stat_error"])
                gamma.append(level0_group.attrs["gamma"])
                tick_time.append(level0_group.attrs["tick_time"])
                interpolation_type.append(level0_group.attrs["inter_type"])
                nu_pre_level0.append(level0_group.attrs["nu_pre"])
                nu_post_level0.append(level0_group.attrs["nu_post"])
                if "level1" in f:
                    level1_group = f.get("level1")
                    nu_pre_level1.append(level1_group.attrs["nu_pre"])
                    nu_post_level1.append(level1_group.attrs["nu_post"])
                else:
                    nu_pre_level1.append(-1)
                    nu_post_level1.append(-1)

    int_auto_correlation_time = np.array(int_auto_correlation_time)
    int_auto_correlation_time_bias = np.array(int_auto_correlation_time_bias)
    int_auto_correlation_time_stat_error = np.array(int_auto_correlation_time_stat_error)
    gamma = np.array(gamma)
    tick_time = np.array(tick_time)
    interpolation_type = np.array(interpolation_type)
    nu_pre_level0 = np.array(nu_pre_level0)
    nu_post_level0 = np.array(nu_post_level0)
    nu_pre_level1 = np.array(nu_pre_level1)
    nu_post_level1 = np.array(nu_post_level1)
    fig_, (ax1_, ax2_, ax3_) = plt.subplots(3, 1, sharex="all", sharey="row", figsize=(12, 5))
    fig_: plt.Figure
    ax1_: plt.Axes
    ax2_: plt.Axes
    ax3_: plt.Axes
    j = 0
    fig_.subplots_adjust(hspace=0, wspace=0)
    base_int_auto_correlation_time = int_auto_correlation_time[nu_pre_level1 == -1]
    base_tick_time = tick_time[nu_pre_level1 == -1]
    ls = []
    labels = []

    ls.append(ax1_.hlines(base_int_auto_correlation_time, 0, 512, colors=list(mcolors.TABLEAU_COLORS.values())[-1]))
    labels.append("HMC")
    ax2_.hlines(base_tick_time, 0, 512, colors=list(mcolors.TABLEAU_COLORS.values())[-1])
    ax3_.hlines(base_int_auto_correlation_time * base_tick_time, 0, 512,
                colors=list(mcolors.TABLEAU_COLORS.values())[-1])

    for i in range(513):
        indices = nu_pre_level1 == i
        x_plot = nu_post_level1[indices]
        y1_plot = int_auto_correlation_time[indices]
        y1_error = int_auto_correlation_time_stat_error[indices] + int_auto_correlation_time_bias[indices]
        y2_plot = tick_time[indices]
        if len(x_plot):
            ls.append(ax1_.errorbar(x_plot, y1_plot, y1_error, marker='.', ls='',
                                    c=list(mcolors.TABLEAU_COLORS.values())[j]))
            labels.append(f"nu pre={i}")

            ax2_.plot(x_plot, y2_plot, marker='.', ls='', c=list(mcolors.TABLEAU_COLORS.values())[j])

            ax3_.errorbar(x_plot, y1_plot * y2_plot, y1_error * y2_plot, marker='.', ls='',
                          c=list(mcolors.TABLEAU_COLORS.values())[j])

            j += 1

    fig_.legend(ls, labels, loc="upper right")
    fig_.subplots_adjust(right=0.85)
    ax3_.set_xlabel(r"$\nu_{post}$")
    ax1_.set_ylabel(r"$\tau$")
    ax1_.set_xscale('log')
    ax1_.set_yscale('log')
    ax2_.set_ylabel(r"t")
    ax2_.set_xscale('log')
    ax2_.set_yscale('log')
    ax3_.set_ylabel(r"$t*\tau$")
    ax3_.set_xscale('log')
    ax3_.set_yscale('log')
    fig_.savefig(sub_folder_name + observable_name + sub_folder_name[:-1] + ".png", dpi=1000)
    fig_.clear()

    fig_, (ax1_, ax2_, ax3_) = plt.subplots(1, 3, sharey="row")
    fig_.subplots_adjust(hspace=0, wspace=0)
    j = []
    k = []
    for i in range(33):
        if np.any(nu_pre_level1 == i):
            j.append(i)
        if np.any(nu_post_level1 == i):
            k.append(i)
    j = np.array(j)
    k = np.array(k)
    data1 = np.zeros((len(j), len(k)))
    data2 = np.zeros((len(j), len(k)))
    data3 = np.zeros((len(j), len(k)))
    for i1, index1 in enumerate(np.sort(j)):
        for i2, index2 in enumerate(np.sort(k)):
            if np.logical_and(nu_pre_level1 == index1, nu_post_level1 == index2).sum() == 1:
                data1[i1, i2] = int_auto_correlation_time[
                    np.logical_and(nu_pre_level1 == index1, nu_post_level1 == index2)]
                data2[i1, i2] = tick_time[np.logical_and(nu_pre_level1 == index1, nu_post_level1 == index2)]
                data3[i1, i2] = tick_time[np.logical_and(nu_pre_level1 == index1, nu_post_level1 == index2)] * \
                                int_auto_correlation_time[
                                    np.logical_and(nu_pre_level1 == index1, nu_post_level1 == index2)]

    im1 = ax1_.imshow(data1)
    ax1_divider = make_axes_locatable(ax1_)
    # Add an axes to the right of the main axes.
    cax1 = ax1_divider.append_axes("right", size="7%", pad="2%")
    fig_.colorbar(im1, cax=cax1)

    im2 = ax2_.imshow(data2)
    ax2_divider = make_axes_locatable(ax2_)
    # Add an axes to the right of the main axes.
    cax2 = ax2_divider.append_axes("right", size="7%", pad="2%")
    fig_.colorbar(im2, cax=cax2)

    im3 = ax3_.imshow(data3)
    ax3_divider = make_axes_locatable(ax3_)
    # Add an axes to the right of the main axes.
    cax3 = ax3_divider.append_axes("right", size="7%", pad="2%")
    fig_.colorbar(im3, cax=cax3)

    ax1_.set_xlabel(r"$\nu_{pre}$")
    ax1_.set_ylabel(r"$\nu_{post}$")
    ax1_.set_title(r"$\tau$")
    ax2_.set_xlabel(r"$\nu_{pre}$")
    # ax2_.set_ylabel(r"$\nu_{post}$")
    ax2_.set_title(r"t")
    ax3_.set_xlabel(r"$\nu_{pre}$")
    # ax3_.set_ylabel(r"$\nu_{post}$")
    ax3_.set_title(r"$\tau$*t")

    fig_.set_tight_layout(True)
    fig_.savefig(sub_folder_name + observable_name + sub_folder_name[:-1] + "_heatmap.png", dpi=1000)
    fig_.clear()

    fig_, (ax1_, ax2_, ax3_) = plt.subplots(3, 1, sharex="all", sharey="row", figsize=(12, 5))
    fig_: plt.Figure
    ax1_: plt.Axes
    ax2_: plt.Axes
    ax3_: plt.Axes
    j = 0
    fig_.subplots_adjust(hspace=0, wspace=0)
    base_int_auto_correlation_time = int_auto_correlation_time[nu_pre_level1 == -1]
    base_tick_time = tick_time[nu_pre_level1 == -1]
    ls = []
    labels = []

    ls.append(ax1_.hlines(base_int_auto_correlation_time, 0, 512, colors=list(mcolors.TABLEAU_COLORS.values())[-1]))
    labels.append("HMC")
    ax2_.hlines(base_tick_time, 0, 512, colors=list(mcolors.TABLEAU_COLORS.values())[-1])
    ax3_.hlines(base_int_auto_correlation_time * base_tick_time, 0, 512,
                colors=list(mcolors.TABLEAU_COLORS.values())[-1])

    indices = nu_pre_level1 == 1
    x_plot = gamma[indices]
    y1_plot = int_auto_correlation_time[indices]
    y1_error = int_auto_correlation_time_stat_error[indices] + int_auto_correlation_time_bias[indices]
    y2_plot = tick_time[indices]
    if len(x_plot):
        ls.append(ax1_.errorbar(x_plot, y1_plot, y1_error, marker='.', ls='',
                                c=list(mcolors.TABLEAU_COLORS.values())[j]))
        labels.append(f"nu pre={1}")

        ax2_.plot(x_plot, y2_plot, marker='.', ls='', c=list(mcolors.TABLEAU_COLORS.values())[j])

        ax3_.errorbar(x_plot, y1_plot * y2_plot, y1_error * y2_plot, marker='.', ls='',
                      c=list(mcolors.TABLEAU_COLORS.values())[j])

        j += 1

    fig_.legend(ls, labels, loc="upper right")
    fig_.subplots_adjust(right=0.85)
    ax3_.set_xlabel(r"$\gamma$")
    ax1_.set_ylabel(r"$\tau$")
    ax1_.set_xscale('log')
    ax1_.set_yscale('log')
    ax2_.set_ylabel(r"t")
    ax2_.set_xscale('log')
    ax2_.set_yscale('log')
    ax3_.set_ylabel(r"$t*\tau$")
    ax3_.set_xscale('log')
    ax3_.set_yscale('log')
    fig_.savefig(sub_folder_name + observable_name + sub_folder_name[:-1] + "_gamma.png", dpi=1000)
    fig_.clear()


# crit_int_auto_correlation_plot("gs_16_CB_ga_1_levels_2/")
# crit_int_auto_correlation_plot("gs_16_BW_ga_1_levels_2/")
# crit_int_auto_correlation_plot("gs_16_CB_ga_2_levels_2/")
# crit_int_auto_correlation_plot("gs_16_BW_ga_2_levels_2/")
# crit_int_auto_correlation_plot("gs_16_CB_pre_1_post_1_levels_2/")
# crit_int_auto_correlation_plot_multiple_levels("gs_16CB_ga_1_levels_x/")
# crit_int_auto_correlation_plot("gs_32_CB_ga_1_levels_2/")
# crit_int_auto_correlation_plot("gs_64_CB_ga_1_levels_2/")
# info_plot("volume_exponent/", magnetization_squared_name)
# info_plot("volume_exponent_test/",magnetization_name)
# info_plot("3d_new_c_0_3/",magnetization_name)
info_plot("volume_exponent_test/",magnetization_name)
# info_plot("3d_new_c_0_3/",magnetization_squared_name)
# info_plot("3d_new_c_0_3/",energy_squared_name)
# check_thermalisation("volume_exponent/")
# base_plot("HMC_physical_check/")
# base_plot("MLHMC_physical_check/")
