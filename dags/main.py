try:
    import sys
    from itertools import chain
    from datetime import datetime
    from datetime import timedelta
    import json
    from airflow import DAG
    from airflow.operators.python_operator import PythonOperator
    from airflow.operators.bash_operator import BashOperator
    from airflow.utils.task_group import TaskGroup
    from all_bkg_mc import create_dag
    #from scatter import *
    print("All Dag modules are ok ......")
except Exception as e:
    print("Error  {} ".format(e))

#home_path = "/usr/local/airlow"
#base_dir = "/usr/local/airflow/data/bsm-search"

thisroot_dir = "/home/abd/root/root/bin"
code_dir = "/home/abd/airflow/code"
base_dir = "/home/abd/airflow/data/bsm-search"

default_args = {
    "owner": "admin",
    'depends_on_past': False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2021, 9, 13),
}

#-----------------------------------------------OPTIONS-----------------------------------------------
mc_options = [
    { 'type': 'mc1', 'mcweight': '0.01875', 'nevents': '40000', 'njobs': 4 },
    { 'type': 'mc2', 'mcweight': '0.0125', 'nevents': '40000', 'njobs': 4 }
]

select_mc_options = [
        { 'region': 'signal', 'variation': 'shape_conv_up', 'suffix': 'shape_conv_up' },
        { 'region': 'signal', 'variation': 'shape_conv_dn', 'suffix': 'shape_conv_dn' },
        { 'region': 'signal', 'variation': 'nominal,weight_var1_up,weight_var1_dn', 'suffix': 'nominal' }
]

hist_shape_mc_options = [
    { 'shapevar': 'shape_conv_up' },
    { 'shapevar': 'shape_conv_dn' }
]

hist_weight_mc_options = [
    { 'shapevar': 'nominal' }
]

signal_options = [
    { 'type': 'sig', 'mcweight': '0.0025', 'nevents': '40000', 'njobs': 2 }
]
#-----------------------------------------------OPTIONS-----------------------------------------------

#-----------------------------------------------LISTS-----------------------------------------------
scatter_mc_tasks_list = []
generate_mc_tasks_list = []
merge_root_mc_tasks_list = []
select_mc_tasks_list = []
hist_shape_mc_tasks_list = []
hist_weight_mc_tasks_list = []
merge_hist_shape_mc_tasks_list = []
merge_hist_all_mc_tasks_list = []
#-----------------------------------------------LISTS-----------------------------------------------

#-----------------------------------------------Operations Start-----------------------------------------------
def scatter (njobs):
    return json.dump([i for i in range(njobs)], sys.stdout)

def scatter_data_generation(type,njobs):
    return {'type':type,'njobs':njobs}
def scatter_op(data):
    type = data['type']
    njobs = data['njobs']
    list = 'scatter'
    check_data = {'type':type,'list':list}
    scatter_operator = PythonOperator(
            task_id = "scatter_{}".format(type),
            python_callable = scatter,
            provide_context = True,
            op_kwargs = {"njobs" : njobs}
        )
    #checkListType(check_data).append(scatter_operator)

def generate_data_generation(type,nevents,jobnumber):
    return {'type':type,'nevents':nevents,'jobnumber':str(jobnumber+1)}
def generate_op(data):
    type = data['type']
    jobnumber = data['jobnumber']
    nevents = data['nevents']
    list = 'generate'
    check_data = {'type':type,'list':list}
    generate_operator = BashOperator(
        task_id = "generate_{}_{}".format(type,jobnumber),
        bash_command = """
            set -x
            source ${thisroot}/thisroot.sh
            pwd
            python ${code}/generatetuple.py ${type} ${nevents} ${base_dir}/${type}_${jobnumber}.root
            """,
        env = {'base_dir': base_dir,'thisroot':thisroot_dir,'code':code_dir,'type': type,'nevents': nevents,'jobnumber':jobnumber},
        )
    #checkListType(check_data).append(generate_operator)

def merge_root_data_generation(type,njobs):
    return {'type':type,'njobs':str(njobs)}
def merge_root_op(data):
    type = data['type']
    njobs = data['njobs']
    list = 'merge_root'
    check_data = {'type':type,'list':list}
    merge_root_operator = BashOperator(
        task_id = "merge_{}".format(type),
        bash_command = """
            set -x
            BASE_DIR=${base_dir}
            BASE=${type}
            END=${njobs}
            INPUTS=""
            for ((c=1;c<${END}+1;c++)); do
                INPUTS="$INPUTS $(printf ${BASE_DIR}/${BASE}_${c}.root)"
            done
            echo Inputs: ${INPUTS}
            source ${thisroot}/thisroot.sh
            hadd -f ${BASE_DIR}/${BASE}.root ${INPUTS}
            """,
        env = {'base_dir': base_dir,'thisroot':thisroot_dir,'type': type,'njobs':njobs},
        )
    #checkListType(check_data).append(merge_root_operator)

def select_data_genertion(type,suffix,region,variation,counter):
    return{
        'inputfile': type+'.root',
        'outputfile': type+'_'+suffix+'.root',
        'region': region,
        'variation': variation,
        'counter':counter
    }
def select_op(data):
    inputfile = data['inputfile']
    outputfile = data['outputfile']
    region = data['region']
    variation = data['variation']
    counter = data['counter']
    list = 'select'
    check_data = {'type':type,'list':list}
    select_operator = BashOperator(
        task_id = "select_{}_{}".format(type,counter+1),
        bash_command = """
            set -x
            source ${thisroot}/thisroot.sh        
            python ${code}/select.py ${base_dir}/${inputfile} ${base_dir}/${outputfile} ${region} ${variation}
            """,
        env = {'base_dir':base_dir,'thisroot':thisroot_dir,'code':code_dir,'inputfile':inputfile,'outputfile':outputfile,'region':region,'variation':variation},
        )
    #checkListType(check_data).append(select_operator)

def hist_shape_data_generation(type,weight,shapevar,variations,counter):
    return {
        'inputfile':type+'_'+shapevar+'.root',
        'outputfile':type+'_'+shapevar+'_hist.root',
        'type':type,
        'weight':weight,
        'shapevar':shapevar,
        'variations':variations,
        'counter':counter
        }
def hist_shape_op(data):
    type = data['type']
    inputfile = data['inputfile']
    outputfile = data['outputfile']
    weight = data['weight']
    variations = data['variations']
    shapevar = data['shapevar']
    counter = data['counter']
    hist_shape_mc = BashOperator(
        task_id = "hist_shape_{}_{}".format(type,counter+1),
        bash_command = """
            set -x
            source ${thisroot}/thisroot.sh        
            variations=$(echo ${variations}|sed 's| |,|g')
            name="${type}_${shapevar}"
            python ${code}/histogram.py ${base_dir}/${inputfile} ${base_dir}/${outputfile} ${type} ${weight} ${variations} ${name}
            """,
        env = {'base_dir': base_dir,'thisroot':thisroot_dir,'code':code_dir,'inputfile':inputfile,'outputfile':outputfile,'type':type,'weight':weight,'shapevar':shapevar,'variations':variations}
        )

def hist_weight_data_generation(type,weight,variations,shapevar,counter):
    inputfile = ''
    outputfile = type+'_hist.root'
    if('mc' in type or 'sig' in type):
        inputfile = type+'_'+shapevar+'.root'
        outputfile = type+'_'+shapevar+'_hist.root'
    elif('data' in type):
        inputfile = type+'_signal.root'
    elif('qcd' in type):
        inputfile = 'data_control.root'
    if('sig' in type):
        type = type+'nal'
    return {
        'inputfile': inputfile,
        'outputfile': outputfile,
        'type': type,
        'weight': weight,
        'variations': variations, 
        'shapevar':shapevar,
        'counter':counter
    }
def hist_weight_op(data):
    type = data['type']
    counter = data['counter']
    shapevar = data['shapevar']
    variations = data['variations']
    weight = data['weight']
    inputfile = data['inputfile']
    outputfile = data['outputfile']

    hist_weight_operator = BashOperator(
        task_id = "hist_weight_{}_{}".format(type,counter+1),
        bash_command = """
            set -x
            source ${thisroot}/thisroot.sh        
            variations=$(echo ${variations}|sed 's| |,|g')
            name=${type}
            python ${code}/histogram.py ${base_dir}/${inputfile} ${base_dir}/${outputfile} ${name} ${weight} ${variations}
            """,
        env = {'base_dir': base_dir,'thisroot':thisroot_dir,'code':code_dir,'inputfile': inputfile,'outputfile':outputfile,'type':type,'weight':weight,'variations':variations},
        )

def merge_explicit_data_generation(operation,type):
    inputfiles = ''
    outputfile = type+'_merged_hist.root'
    if('mc' in type):
        if('merge_hist_shape' in operation):
            inputfiles = type+'_shape_conv_up_hist.root '+type+'_shape_conv_dn_hist.root'
            outputfile = type+'_shape_hist.root'
        elif('merge_hist_all' in operation):
            inputfiles = type+'_nominal_hist.root '+type+'_shape_hist.root'
    elif('sig' in type):
        inputfiles = type+'_nominal_hist.root'
    elif('data' in type):
        inputfiles = type+"_hist.root qcd_hist.root"
    elif('all' in type):
        inputfiles = "mc1_merged_hist.root mc2_merged_hist.root sig_merged_hist.root data_merged_hist.root"
        outputfile = "all_merged_hist.root"      
    return{
        'type': type,
        'operation':operation,
        'inputfiles': inputfiles,
        'outputfile': outputfile
    }
def merge_explicit_op(data):
    type = data['type']
    operation = data['operation']
    inputfiles = data['inputfiles']
    outputfile = data['outputfile']
    merge_hist_shape_mc = BashOperator(
        task_id = operation+"_"+type,
        bash_command = """
            set -x
            inputfiles=${inputfiles}
            INPUTS=""
            for i in ${inputfiles}; do
            INPUTS="${INPUTS} $(printf ${base_dir}/${i})"
            done
            source ${thisroot}/thisroot.sh        
            hadd -f ${base_dir}/${outputfile} ${INPUTS}
            """,
        env = {'base_dir': base_dir,'thisroot':thisroot_dir,'inputfiles':inputfiles,'outputfile':outputfile},
        )

def makews_data_generation(data_bkg_hists,workspace_prefix,xml_dir):
    return {
        'data_bkg_hists':data_bkg_hists,
        'workspace_prefix':workspace_prefix,
        'xml_dir':xml_dir
    }
def makews_op(data):
    data_bkg_hists = data['data_bkg_hists']
    workspace_prefix = data['workspace_prefix']
    xml_dir = data['xml_dir']
    makews_operator = BashOperator(
        task_id = "makews",
        bash_command = """
            set -x
            source ${thisroot}/thisroot.sh
            python ${code}/makews.py ${base_dir}/${data_bkg_hists} ${workspace_prefix} ${xml_dir}
        """,
        env = {'base_dir': base_dir,'thisroot':thisroot_dir,'code':code_dir,'data_bkg_hists': data_bkg_hists,'workspace_prefix':workspace_prefix,'xml_dir':xml_dir}
    )

def plot_data_generation(combined_model,nominal_vals,fit_results,prefit_plot,postfit_plot):
    return {
        'combined_model':combined_model,
        'nominal_vals':nominal_vals,
        'fit_results':fit_results,
        'prefit_plot':prefit_plot,
        'postfit_plot':postfit_plot
        }
def plot_op(data):
    combined_model = data['combined_model']
    nominal_vals = data['nominal_vals']
    fit_results = data['fit_results']
    prefit_plot = data['prefit_plot']
    postfit_plot = data['postfit_plot']
    plot_operator = BashOperator(
        task_id = "plot",
        bash_command = """
            set -x
            source ${thisroot}/thisroot.sh
            hfquickplot write-vardef ${base_dir}/${combined_model} combined ${base_dir}/${nominal_vals}
            hfquickplot plot-channel ${base_dir}/${combined_model} combined channel1 x ${base_dir}/${nominal_vals} -c qcd,mc2,mc1,signal -o ${base_dir}/${prefit_plot}
            hfquickplot fit ${base_dir}/${combined_model} combined ${base_dir}/${fit_results}
            hfquickplot plot-channel ${base_dir}/${combined_model} combined channel1 x ${base_dir}/${fit_results} -c qcd,mc2,mc1,signal -o ${base_dir}/${postfit_plot}
        """,
        env = {'base_dir': base_dir,'thisroot':thisroot_dir,'combined_model': combined_model,'nominal_vals':nominal_vals,'fit_results':fit_results,'prefit_plot':prefit_plot,'postfit_plot':postfit_plot},
        )
#-----------------------------------------------Operations End-----------------------------------------------

with DAG(dag_id="main", schedule_interval="@daily", default_args=default_args, catchup=False) as dag:
 
    perpare_dir = BashOperator(
        task_id = "perpare_dir",
        bash_command = """
        set -x
        rm -rf $base_dir
        mkdir -p $base_dir
        """,
        env = {'base_dir': base_dir},
    )
    #-----------------------------------------------MC Workflow Start-----------------------------------------------
    with TaskGroup(group_id='mc') as mc:
        for i in range(len(mc_options)):
            type = mc_options[i]['type']
            njobs = mc_options[i]['njobs']
            nevents = mc_options[i]['nevents']
            mcweight = mc_options[i]['mcweight']
            with TaskGroup(group_id='{}'.format(type)) as submc:
                with TaskGroup(group_id='scatter_group_{}'.format(type)) as tg:
                    scatter_data = scatter_data_generation(type,njobs)
                    scatter_op(scatter_data)
                scatter_mc_tasks_list.append(tg)
                
                with TaskGroup(group_id='generate_group_{}'.format(type)) as tg:
                    for j in range(njobs):
                        generate_data = generate_data_generation(type,nevents,j)
                        generate_op(generate_data)
                generate_mc_tasks_list.append(tg)

                with TaskGroup(group_id='merge_root_group_{}'.format(type)) as tg:
                    merge_root_data = merge_root_data_generation(type,njobs)
                    merge_root_op(merge_root_data)
                merge_root_mc_tasks_list.append(tg)

                with TaskGroup(group_id='select_group_{}'.format(type)) as tg:
                    for j in range (len(select_mc_options)):
                        suffix = select_mc_options[j]['suffix']
                        region = select_mc_options[j]['region']
                        variation = select_mc_options[j]['variation']
                        select_data = select_data_genertion(type,suffix,region,variation,j)
                        select_op(select_data)
                select_mc_tasks_list.append(tg)

                with TaskGroup(group_id='hist_shape_group_{}'.format(type)) as tg:
                    for j in range (len(hist_shape_mc_options)):
                        shapevar = hist_shape_mc_options[j]['shapevar']
                        variations = 'nominal'
                        hist_shape_data = hist_shape_data_generation(type,mcweight,shapevar,variations,j)
                        hist_shape_op(hist_shape_data)
                hist_shape_mc_tasks_list.append(tg)

                with TaskGroup(group_id='hist_weight_group_{}'.format(type)) as tg:
                    for j in range (len(hist_weight_mc_options)):
                        shapevar = hist_weight_mc_options[j]['shapevar']
                        variations = 'nominal,weight_var1_up,weight_var1_dn'
                        hist_weight_data = hist_weight_data_generation(type,mcweight,variations,shapevar,j)
                        hist_weight_op(hist_weight_data)
                hist_weight_mc_tasks_list.append(tg)
                
                with TaskGroup(group_id='merge_hist_shape_group_{}'.format(type)) as tg:
                    merge_hist_shape_data = merge_explicit_data_generation("merge_hist_shape",type)
                    merge_explicit_op(merge_hist_shape_data)
                merge_hist_shape_mc_tasks_list.append(tg)
                
                with TaskGroup(group_id='merge_hist_all_group_{}'.format(type)) as tg:
                    merge_hist_all_data = merge_explicit_data_generation("merge_hist_all",type)
                    merge_explicit_op(merge_hist_all_data)
                merge_hist_all_mc_tasks_list.append(tg)
    #-----------------------------------------------MC Workflow End-----------------------------------------------

    #-----------------------------------------------Signal Workflow Start-----------------------------------------------
    with TaskGroup(group_id='singal') as signal:
        signal_options = [{'type':'sig','mcweight':'0.0025','nevents':'40000','njobs':2}]
        select_signal_options = [{'region':'signal','variation':'nominal','suffix':'nominal'}]
        hist_weight_signal_options = [{'shapevar':'nominal'}]
        scatter_signal_tasks_list = []
        generate_signal_tasks_list = []
        merge_root_signal_tasks_list = []
        select_signal_tasks_list = []
        hist_weight_signal_tasks_list = []
        merge_hist_all_signal_tasks_list = []
        for i in range(len(signal_options)):
            type = signal_options[i]['type']
            njobs = signal_options[i]['njobs']
            nevents = signal_options[i]['nevents']
            mcweight = signal_options[i]['mcweight']

            with TaskGroup(group_id='scatter_group_{}'.format(type)) as tg:
                scatter_data = scatter_data_generation(type,njobs)
                scatter_op(scatter_data)
            scatter_signal_tasks_list.append(tg)

            with TaskGroup(group_id='generate_group_{}'.format(type)) as tg:
                for j in range(njobs):
                    generate_data = generate_data_generation(type,nevents,j)
                    generate_op(generate_data)
            generate_signal_tasks_list.append(tg)
            
            with TaskGroup(group_id='merge_root_group_{}'.format(type)) as tg:
                merge_root_data = merge_root_data_generation(type,njobs)
                merge_root_op(merge_root_data)
            merge_root_signal_tasks_list.append(tg)

            with TaskGroup(group_id='select_group_{}'.format(type)) as tg:
                for j in range (len(select_signal_options)):
                    suffix = select_signal_options[j]['suffix']
                    region = select_signal_options[j]['region']
                    variation = select_signal_options[j]['variation']
                    select_data = select_data_genertion(type,suffix,region,variation,j)
                    print(select_data)
                    select_op(select_data)
            select_signal_tasks_list.append(tg)

            with TaskGroup(group_id='hist_weight_group_{}'.format(type)) as tg:
                for j in range (len(hist_weight_signal_options)):
                    shapevar = hist_weight_signal_options[j]['shapevar']
                    variations = 'nominal'
                    hist_weight_data = hist_weight_data_generation(type,mcweight,variations,shapevar,j)
                    hist_weight_op(hist_weight_data)
            hist_weight_signal_tasks_list.append(tg)
            
            with TaskGroup(group_id='merge_hist_all_group_{}'.format(type)) as tg:
                merge_hist_all_data = merge_explicit_data_generation("merge_hist_all",type)
                merge_explicit_op(merge_hist_all_data)
            merge_hist_all_signal_tasks_list.append(tg)
    #-----------------------------------------------Signal Workflow End-----------------------------------------------

    #-----------------------------------------------Data Workflow Start-----------------------------------------------
    with TaskGroup(group_id='data') as data:
        data_options = [{'type':'data','nevents':'20000','njobs':5}]
        data_select_signal_options = [{'region':'signal','variation':'nominal','suffix':'signal'}]
        data_select_control_options = [{'region':'control','variation':'nominal','suffix':'control'}]
        data_hist_signal_options = [{'shapevar':'nominal'}]
        data_hist_control_options = [{'shapevar':'nominal','type':'qcd'}]
        scatter_data_tasks_list = []
        generate_data_tasks_list = []
        merge_root_data_tasks_list = []
        data_select_signal_tasks_list = []
        data_select_control_tasks_list = []
        data_hist_signal_tasks_list = []
        data_hist_control_tasks_list = []
        merge_hist_all_data_tasks_list = []

        for i in range(len(data_options)):
            type = data_options[i]['type']
            njobs = data_options[i]['njobs']
            nevents = data_options[i]['nevents']

            with TaskGroup(group_id='scatter_group_{}'.format(type)) as tg:
                scatter_data = scatter_data_generation(type,njobs)
                scatter_op(scatter_data)
            scatter_data_tasks_list.append(tg)

            with TaskGroup(group_id='generate_group_{}'.format(type)) as tg:
                for j in range(njobs):
                    generate_data = generate_data_generation(type,nevents,j)
                    generate_op(generate_data)
            generate_data_tasks_list.append(tg)

            with TaskGroup(group_id='merge_root_group_{}'.format(type)) as tg:
                merge_root_data = merge_root_data_generation(type,njobs)
                merge_root_op(merge_root_data)
            merge_root_data_tasks_list.append(tg)

            with TaskGroup(group_id='select_signal_group_{}'.format(type)) as tg:
                for j in range (len(data_select_signal_options)):
                    suffix = data_select_signal_options[j]['suffix']
                    region = data_select_signal_options[j]['region']
                    variation = data_select_signal_options[j]['variation']
                    select_data = select_data_genertion(type,suffix,region,variation,j)
                    select_op(select_data)
            data_select_signal_tasks_list.append(tg)

            with TaskGroup(group_id='select_control_group_{}'.format(type)) as tg:
                for j in range (len(data_select_control_options)):
                    suffix = data_select_control_options[j]['suffix']
                    region = data_select_control_options[j]['region']
                    variation = data_select_control_options[j]['variation']
                    select_data = select_data_genertion(type,suffix,region,variation,j)
                    select_op(select_data)
            data_select_control_tasks_list.append(tg)
            
            with TaskGroup(group_id='hist_signal_group_{}'.format(type)) as tg:
                for j in range (len(data_hist_signal_options)):
                    shapevar = data_hist_signal_options[j]['shapevar']
                    mcweight = '1.0'
                    variations = 'nominal'
                    hist_weight_data = hist_weight_data_generation(type,mcweight,variations,shapevar,j)
                    hist_weight_op(hist_weight_data)
            data_hist_signal_tasks_list.append(tg)

            with TaskGroup(group_id='hist_control_group_{}'.format(type)) as tg:
                for j in range (len(data_hist_control_options)):
                    qcd = data_hist_control_options[j]['type']
                    shapevar = data_hist_control_options[j]['shapevar']
                    mcweight = '0.1875'
                    variations = 'nominal'
                    hist_weight_data = hist_weight_data_generation(qcd,mcweight,variations,shapevar,j)
                    hist_weight_op(hist_weight_data)
            data_hist_control_tasks_list.append(tg)

            with TaskGroup(group_id='merge_hist_all_group_{}'.format(type)) as tg:
                merge_hist_all_data = merge_explicit_data_generation("merge_hist_all",type)
                merge_explicit_op(merge_hist_all_data)
            merge_hist_all_data_tasks_list.append(tg)
    #-----------------------------------------------Data Workflow End-----------------------------------------------

    #-----------------------------------------------Merge All Start-----------------------------------------------
    with TaskGroup(group_id='merge_hist_all') as merge_hist_all:
        type = 'all'
        merge_hist_all_data = merge_explicit_data_generation("merge_hist_all",type)
        merge_explicit_op(merge_hist_all_data)
    #-----------------------------------------------Merge All End-----------------------------------------------        
    
    #-----------------------------------------------Makews Start-----------------------------------------------        
    with TaskGroup(group_id='makews') as makews:
        data_bkg_hists = "all_merged_hist.root"
        workspace_prefix = base_dir+"/results"
        xml_dir = base_dir+"/xmldir"
        makews_data = makews_data_generation(data_bkg_hists,workspace_prefix,xml_dir)
        makews_op(makews_data)
    #-----------------------------------------------Makews End-----------------------------------------------        

    #-----------------------------------------------Plot Start-----------------------------------------------        
    with TaskGroup(group_id='plot') as plot:
        combined_model = 'results_combined_meas_model.root'
        nominal_vals = 'nominal_vals.yml'
        fit_results = 'fit_results.yml'
        prefit_plot = 'prefit.pdf'
        postfit_plot = 'postfit.pdf'
        plot_data = plot_data_generation(combined_model,nominal_vals,fit_results,prefit_plot,postfit_plot)
        plot_op(plot_data)
    #-----------------------------------------------Plot End-----------------------------------------------        
    
#-----------------------------------------------Dependencies-----------------------------------------------
perpare_dir >> scatter_mc_tasks_list
#scatter_mc_tasks_list[0] >> [generate_mc_tasks_list[j] for j in range (4)] >> merge_root_mc_tasks_list[0] >> [select_mc_tasks_list[j] for j in range (3)] >> hist_shape_mc_tasks_list[0] >> merge_hist_shape_mc_tasks_list[0]
#scatter_mc_tasks_list[1] >> [generate_mc_tasks_list[j] for j in range (4,8)] >> merge_root_mc_tasks_list[1] >> [select_mc_tasks_list[j] for j in range (3,6)] >> hist_shape_mc_tasks_list[1] >> merge_hist_shape_mc_tasks_list[1]
#[select_mc_tasks_list[j] for j in range (3)] >> hist_weight_mc_tasks_list[0]
#[select_mc_tasks_list[j] for j in range (3,6)] >> hist_weight_mc_tasks_list[1]
scatter_mc_tasks_list[0] >> generate_mc_tasks_list[0] >> merge_root_mc_tasks_list[0] >> select_mc_tasks_list[0] >> hist_shape_mc_tasks_list[0] >> merge_hist_shape_mc_tasks_list[0]
scatter_mc_tasks_list[1] >> generate_mc_tasks_list[1] >> merge_root_mc_tasks_list[1] >> select_mc_tasks_list[1] >> hist_shape_mc_tasks_list[1] >> merge_hist_shape_mc_tasks_list[1]
select_mc_tasks_list[0] >> hist_weight_mc_tasks_list[0]
select_mc_tasks_list[1] >> hist_weight_mc_tasks_list[1]
[merge_hist_shape_mc_tasks_list[0],hist_weight_mc_tasks_list[0]] >> merge_hist_all_mc_tasks_list[0]
[merge_hist_shape_mc_tasks_list[1],hist_weight_mc_tasks_list[1]] >> merge_hist_all_mc_tasks_list[1]

for i in range(len(signal_options)):
    perpare_dir >> scatter_signal_tasks_list[i] >> generate_signal_tasks_list[i] >> merge_root_signal_tasks_list[i] >> select_signal_tasks_list[i] >> hist_weight_signal_tasks_list[i] >> merge_hist_all_signal_tasks_list[i]

for i in range(len(data_options)):
    perpare_dir >> scatter_data_tasks_list[i] >> generate_data_tasks_list[i] >> merge_root_data_tasks_list[i]
    merge_root_data_tasks_list[i] >> data_select_signal_tasks_list[i] >> data_hist_signal_tasks_list[i]
    merge_root_data_tasks_list[i] >> data_select_control_tasks_list[i] >> data_hist_control_tasks_list[i]
    [data_hist_signal_tasks_list[i],data_hist_control_tasks_list[i]] >> merge_hist_all_data_tasks_list[i]

merge_hist_all_mc_tasks_list >> merge_hist_all
merge_hist_all_signal_tasks_list >> merge_hist_all
merge_hist_all_data_tasks_list >> merge_hist_all
merge_hist_all >> makews >> plot
